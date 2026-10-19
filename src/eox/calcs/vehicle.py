"""Whole-machine checks: mass split, static stability, turning, steering
effort, and the articulation pinch zone."""

from __future__ import annotations

import math

import numpy as np

from eox.calcs.common import G0, Report
from eox.checks import Check
from eox.tractor import HALVES


def tip_angle(cg, edges, headings: int = 360) -> float:
    """Smallest ground slope (deg), over every downhill direction, at which
    the gravity line through `cg` leaves the support polygon `edges`.

    For edge a->b (unit u) and downhill direction d, gravity in the machine
    frame is g = sin(th) d - cos(th) z. The moment about the edge,
    ((c - a) x g) . u = sin(th) M1 - cos(th) M0, changes sign at
    tan(th) = M0 / M1 when M0 and M1 share a sign. Edges may be inclined
    (an elevated pivot point), which this handles exactly."""
    c = np.asarray(cg, float)
    phi = np.linspace(0, 2 * np.pi, headings, endpoint=False)
    d = np.stack([np.cos(phi), np.sin(phi), np.zeros_like(phi)], axis=1)
    best = np.full(headings, 90.0)
    for a, b in edges:
        a, b = np.asarray(a, float), np.asarray(b, float)
        u = (b - a) / np.linalg.norm(b - a)
        ca = c - a
        M0 = np.dot(np.cross(ca, [0, 0, 1.0]), u)
        M1 = np.cross(ca, d) @ u
        ok = (M0 * M1) > 0
        th = np.degrees(np.arctan(np.divide(M0, M1, out=np.full_like(M1, np.inf), where=M1 != 0)))
        best = np.where(ok & (th > 0), np.minimum(best, th), best)
    return float(best.min())


def _ring(points):
    """Polygon edges, points ordered around their centroid in plan."""
    cx = sum(q[0] for q in points) / len(points)
    cy = sum(q[1] for q in points) / len(points)
    pts = sorted(points, key=lambda q: math.atan2(q[1] - cy, q[0] - cx))
    return list(zip(pts, pts[1:] + pts[:1]))


def stability(tr, gamma: float) -> dict[str, float]:
    """Tip angles for one articulation angle.
    rigid: all four wheels, whole-machine CG (oscillation joint at its stop).
    front/rear: each half's stability triangle, its two wheels + the pivot.
    The pivot locks pitch, so a half can only tip sideways, about the lines
    from its wheels to the pivot, never back over its own axle."""
    out = {"rigid": tip_angle(tr.cg(None, gamma), _ring(tr.contacts("front", gamma) + tr.contacts("rear", gamma)))}
    j = tr.joint()
    for half in HALVES:
        left, right = tr.contacts(half, gamma)
        out[half] = tip_angle(tr.cg(half, gamma), [(left, j), (right, j)])
    return out


def _plan_corners(b):
    x0, x1, y0, y1, _, _ = b.bounds()
    return [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]


def run(p, tr, r: Report):
    v, lo, a, st = p.vehicle, p.layout, p.axle, p.steering
    loads = tr.axle_loads_n()
    m_machine = tr.mass() - v.mass_operator_kg - v.mass_payload_kg
    grp = "Vehicle"
    cg = tr.cg()
    r.add(
        Check(grp, "machine mass (no operator)", round(m_machine), "kg"),
        Check(grp, "mass with operator: front / rear half", f"{tr.mass('front'):.0f} / {tr.mass('rear'):.0f}", "kg"),
        Check(grp, "axle load split front / rear", f"{loads['front'] / (loads['front'] + loads['rear']) * 100:.0f} / "
              f"{loads['rear'] / (loads['front'] + loads['rear']) * 100:.0f}", "%",
              note="a front implement (deck) moves this toward 50/50"),
        Check(grp, "CG x / y / z (with operator)", f"{cg[0]:.0f} / {cg[1]:.0f} / {cg[2]:.0f}", "mm",
              note="origin on the ground under the pivot"),
    )

    # ---- turning ----------------------------------------------------------------
    gmax = math.radians(lo.articulation_max_deg)
    af, ar = lo.front_axle_x, -lo.rear_axle_x
    R = max((af * math.cos(gmax) + ar) / math.sin(gmax), (ar * math.cos(gmax) + af) / math.sin(gmax))
    r.add(Check(grp, f"turning radius, outer tyre at {lo.articulation_max_deg:g} deg", round((R + a.track / 2 + a.tire_width / 2) / 1000, 2),
                "m", note="articulated: both axles track the same arc when a = b"))

    # ---- stability ------------------------------------------------------------------
    grp = "Stability"
    worst = 90.0
    for gamma, label in ((0.0, "straight"), (lo.articulation_max_deg, f"articulated {lo.articulation_max_deg:g} deg")):
        s = stability(tr, gamma)
        worst = min(worst, *s.values())
        r.add(Check(grp, f"tip angle, {label}: rigid / front half / rear half",
                    f"{s['rigid']:.0f} / {s['front']:.0f} / {s['rear']:.0f}", "deg",
                    note="worst slope direction; a half starts to roll onto its oscillation stop at its own angle"))
    r.add(Check(grp, "max working slope (half the lowest tip angle)", round(worst / 2, 1), "deg",
                v.design_slope_deg, ">=", warn_limit=v.max_slope_deg,
                note="industry practice, not a confirmed standard value: B71.1 stability numbers still to verify"))

    # ---- steering ---------------------------------------------------------------------
    grp = "Steering"
    M_f = st.scrub_coefficient * loads["front"] * af / 1000
    M_r = st.scrub_coefficient * loads["rear"] * ar / 1000
    M_req = max(M_f, M_r)
    A_full = math.pi / 4 * st.bore ** 2
    A_rod = math.pi / 4 * (st.bore ** 2 - st.rod ** 2)
    M_cyl = st.relief_bar * 0.1 * A_rod * st.lever_arm / 1000 * math.cos(gmax)
    stroke = 2 * st.lever_arm * math.sin(gmax)
    t_cyl = stroke * (A_full + A_rod) / 2 / (st.pump_flow_lpm * 1e6 / 60)
    M_el = st.electric_actuator_force_n * st.lever_arm / 1000 * math.cos(gmax)
    t_el = stroke / st.electric_actuator_speed_mm_s
    r.add(
        Check(grp, "articulation moment needed at standstill", round(M_req), "N*m",
              note=f"tyre scrub {st.scrub_coefficient:g} x axle load x axle-to-pivot; front {M_f:.0f}, rear {M_r:.0f}"),
        Check(grp, f"cylinder moment at full lock ({st.bore:g} mm bore, {st.relief_bar:g} bar, rod side)", round(M_cyl), "N*m",
              round(M_req), ">=", 0.15),
        Check(grp, f"lock-to-lock time ({st.pump_flow_lpm:g} L/min)", round(t_cyl, 1), "s", st.lock_to_lock_target_s, "<="),
        Check(grp, "electric actuator alternative: moment / lock-to-lock", f"{M_el:.0f} N*m / {t_el:.0f} s", "",
              note=f"{st.electric_actuator_force_n:g} N actuator near full load: too slow to steer with"),
    )

    # ---- articulation pinch zone ----------------------------------------------------------
    # Front-half parts swing toward the operator's footwell at full lock.
    x_front = lo.footrest_front_x
    fw = (x_front - 220, x_front, -(lo.frame_half_width + 40), lo.frame_half_width + 40)
    corners = [c for half, _, b in tr.bodies if half == "front" for c in _plan_corners(b)]
    L, W, _ = tr.box.outer
    bx = tr.box_pos[0]
    corners += [(bx + sx * L / 2, sy * W / 2) for sx in (-1, 1) for sy in (-1, 1)]
    gap = math.inf
    for g in (gmax, -gmax):
        for x, y in corners:
            xr, yr = x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g)
            dx = max(fw[0] - xr, 0, xr - fw[1])
            dy = max(fw[2] - yr, 0, yr - fw[3])
            gap = min(gap, math.hypot(dx, dy))
    r.add(Check(grp, "front half to footwell at full lock (pinch gap)", round(gap), "mm", 120, ">=",
                note="120 mm = ISO 13854 minimum gap for a foot (verify against the standard)"))

    # ---- deck mounting (open decision) --------------------------------------------------------
    d = p.deck
    r.add(Check("Deck", "drive-over: diff clearance minus deck top at min cut", a.diff_clearance - d.top_height_min_cut,
                "mm", note=f"mount = {d.mount}; negative means the front axle can't roll over the deck"))
    r.values.update(worst_tip=worst, M_steer=M_req)
