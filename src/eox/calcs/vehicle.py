"""Whole-machine checks: mass split, static stability, turning, steering
effort, and (Pro) the articulation joint's clearances."""

from __future__ import annotations

import math

import numpy as np

from eox.calcs.common import Report
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


def stability(tr, gamma: float = 0.0) -> dict[str, float]:
    """Tip angles. rigid: all four wheels, whole-machine CG.
    Pro only, front/rear: each half's stability triangle (its two wheels + the
    pivot). The pivot locks pitch, so a half can only tip sideways, about the
    lines from its wheels to the pivot, never back over its own axle."""
    four = tr.contacts("front", gamma) + tr.contacts("rear", gamma)
    out = {"rigid": tip_angle(tr.cg(None, gamma), _ring(four))}
    if tr.articulated:
        j = tr.joint()
        for half in HALVES:
            left, right = tr.contacts(half, gamma)
            out[half] = tip_angle(tr.cg(half, gamma), [(left, j), (right, j)])
    elif getattr(tr.p.steer_axle, "oscillates", False):
        f = tr.axle("front")
        pivot = (f.x, 0.0, f.tire_diameter / 2)
        out["triangle"] = tip_angle(tr.cg(), _ring(tr.contacts("rear") + [pivot]))
    return out


def _plan_rect(b, g=0.0):
    x0, x1, y0, y1, _, _ = b.bounds()
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [(x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g)) for x, y in pts]


def _overlap(p1, p2) -> bool:
    """Separating-axis test for two convex plan polygons."""
    for poly in (p1, p2):
        for i in range(len(poly)):
            ax, ay = poly[i]
            bx, by = poly[(i + 1) % len(poly)]
            nx, ny = by - ay, ax - bx
            s1 = [nx * x + ny * y for x, y in p1]
            s2 = [nx * x + ny * y for x, y in p2]
            if max(s1) <= min(s2) or max(s2) <= min(s1):
                return False
    return True


def halves_collide(tr, gamma: float) -> list[str]:
    """Pro: pairs of front- and rear-half parts that would hit at articulation
    gamma (plan polygons + height overlap). Joint parts are meant to nest."""
    from eox.powerbox import Body

    L, W, H = tr.box.outer
    bx, _, bz = tr.box_pos
    front = [b for g, k, b in tr.bodies if g == "front" and k != "pivot"]
    front.append(Body("power box", "box", (bx, 0, bz + H / 2), (L, W, H)))
    rear = [b for g, k, b in tr.bodies if g == "rear" and k != "pivot"]
    g = math.radians(gamma)
    hits = []
    for fb in front:
        fz = fb.bounds()[4:]
        for rb in rear:
            rz = rb.bounds()[4:]
            if fz[1] > rz[0] and rz[1] > fz[0] and _overlap(_plan_rect(fb, g), _plan_rect(rb)):
                hits.append(f"{fb.name} / {rb.name}")
    return hits


# Parts that are meant to touch or nest: an axle and its wheels/tube/gear
# case/motor, the frame members among themselves, the seat's own pieces.
_JOINED = {frozenset(k) for k in (("wheel", "axle"), ("axle", "motor"), ("frame", "frame"), ("seat", "seat"),
                                   ("axle", "axle"), ("pivot", "pivot"), ("pivot", "frame"), ("steering", "axle"),
                                   ("steering", "frame"), ("implement", "frame"), ("controller", "frame"))}


def parts_overlap(tr) -> list[str]:
    """Overlapping bounding boxes within each rigid group, plus the power box,
    ignoring pairs that are joined by design."""
    from eox.powerbox import Body

    L, W, H = tr.box.outer
    bx, _, bz = tr.box_pos
    items = [(g, k, b) for g, k, b in tr.bodies]
    items.append((tr.box_group, "powerbox", Body("power box", "box", (bx, 0, bz + H / 2), (L, W, H))))
    hits = []
    for i, (g1, k1, b1) in enumerate(items):
        for g2, k2, b2 in items[i + 1:]:
            if g1 != g2 or frozenset((k1, k2)) in _JOINED:
                continue
            A, B = b1.bounds(), b2.bounds()
            if min(A[1], B[1]) - max(A[0], B[0]) > 1 and min(A[3], B[3]) - max(A[2], B[2]) > 1 \
                    and min(A[5], B[5]) - max(A[4], B[4]) > 1:
                hits.append(f"{b1.name} / {b2.name}")
    return hits


def run(p, tr, r: Report):
    v, a = p.vehicle, p.axle
    loads = tr.axle_loads_n()
    m_machine = tr.mass() - v.mass_operator_kg - v.mass_payload_kg
    grp = "Vehicle"
    cg = tr.cg()
    split = loads["front"] / (loads["front"] + loads["rear"]) * 100
    r.add(Check(grp, "machine mass (no operator)", round(m_machine), "kg"))
    if tr.articulated:
        r.add(Check(grp, "mass with operator: front / rear half", f"{tr.mass('front'):.0f} / {tr.mass('rear'):.0f}", "kg"))
    r.add(
        Check(grp, "axle load split front / rear (with operator)", f"{split:.0f} / {100 - split:.0f}", "%",
              note="a front implement moves this forward"),
        Check(grp, "CG x / y / z (with operator)", f"{cg[0]:.0f} / {cg[1]:.0f} / {cg[2]:.0f}", "mm",
              note="origin on the ground under the pivot" if tr.articulated else "origin on the ground under the rear axle"),
    )
    if tr.articulated:
        _pro_turning_and_steering(p, tr, r, loads)
    else:
        _home_turning_and_steering(p, tr, r, loads)
    hits = parts_overlap(tr)
    r.add(Check(grp, "major parts clear each other (power box, units, axles, seat, frame)", len(hits), "overlaps", 0, "<=",
                note="; ".join(hits) if hits else "box outlines within each rigid group"))

    # ---- stability ------------------------------------------------------------------
    grp = "Stability"
    angles = [0.0] + ([p.layout.articulation_max_deg] if tr.articulated else [])
    worst = 90.0
    for gamma in angles:
        s = stability(tr, gamma)
        worst = min(worst, *s.values())
        label = "straight" if not gamma else f"articulated {gamma:g} deg"
        if tr.articulated:
            r.add(Check(grp, f"tip angle, {label}: rigid / front half / rear half",
                        f"{s['rigid']:.0f} / {s['front']:.0f} / {s['rear']:.0f}", "deg",
                        note="worst slope direction; a half starts to roll onto its oscillation stop at its own angle"))
        else:
            r.add(Check(grp, "tip angle, four wheels" + (" / front-axle triangle" if "triangle" in s else ""),
                        " / ".join(f"{s[k]:.0f}" for k in s), "deg", note="worst slope direction"))
    r.add(Check(grp, "max working slope (half the lowest tip angle)", round(worst / 2, 1), "deg",
                v.design_slope_deg, ">=", warn_limit=v.max_slope_deg,
                note="industry practice, not a confirmed standard value: B71.1 stability numbers still to verify"))

    # ---- deck mounting (open decision, issue 7) ---------------------------------------
    d, front = p.deck, tr.axle("front")
    r.add(Check("Deck", "drive-over: front axle clearance minus deck top at min cut",
                front.clearance - d.top_height_min_cut, "mm",
                note=f"mount = {d.mount}; the front axle must roll over a mid-mount deck, negative means it can't"))
    r.values.update(worst_tip=worst)


def _pro_turning_and_steering(p, tr, r, loads):
    lo, a, st = p.layout, p.axle, p.steering
    gmax = math.radians(lo.articulation_max_deg)
    af, ar = lo.front_axle_x, -lo.rear_axle_x
    R = max((af * math.cos(gmax) + ar) / math.sin(gmax), (ar * math.cos(gmax) + af) / math.sin(gmax))
    r.add(Check("Vehicle", f"turning radius, outer tyre at {lo.articulation_max_deg:g} deg",
                round((R + a.track / 2 + a.tire_width / 2) / 1000, 2), "m",
                note="articulated: both axles track the same arc when a = b"))

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

    # ---- articulation joint clearances ----------------------------------------------
    grp = "Pivot"
    hits = sorted({h for gm in (lo.articulation_max_deg, -lo.articulation_max_deg) for h in halves_collide(tr, gm)})
    r.add(Check(grp, f"front and rear halves clear each other at +-{lo.articulation_max_deg:g} deg", len(hits), "collisions",
                0, "<=", note="; ".join(hits) if hits else "plan outlines + heights of every part except the joint itself"))
    x_front = lo.footrest_front_x
    fw = (x_front - 220, x_front, -(lo.frame_half_width + 40), lo.frame_half_width + 40)
    corners = [c for g, _, b in tr.bodies if g == "front" for c in _plan_rect(b)]
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
                note="ISO 13854 minimum gap for a foot is 120 mm; for a body 500 mm (guard or keep clear)"))

    # Pin loads. Free body of the rear half: rear axle reaction, its own
    # weight, and the joint. The joint carries a vertical force (thrust on the
    # bearing faces) and the pitch moment, which the two vertical pins take as
    # a fore-aft couple. Add fore-aft and lateral shares, times the design g.
    ld = p.loads
    g0 = 9.81
    W_r = tr.mass("rear") * g0
    x_rc = tr.cg("rear")[0]
    N_r = loads["rear"]
    M_pitch = abs(W_r * x_rc - N_r * lo.rear_axle_x)                       # N*mm
    F_couple = ld.vertical_g * M_pitch / lo.pin_spacing
    F_long = ld.longitudinal_g * W_r / 2
    F_lat = ld.lateral_g * W_r / 2
    F_pin = math.hypot(F_couple + F_long, F_lat)
    d, t = lo.pin_diameter, lo.ear_thickness
    tau = F_pin / (2 * math.pi * d * d / 4)                                  # double shear
    sig_b = F_pin / (2 * d * t)                                              # two ears per pin
    r.add(
        Check(grp, "pitch moment through the joint (static)", round(M_pitch / 1000), "N*m",
              note="the pivot locks pitch, so the halves share it; taken by the pin couple"),
        Check(grp, f"load per pin at {ld.vertical_g:g} g + {ld.longitudinal_g:g} g fore-aft + {ld.lateral_g:g} g side",
              round(F_pin / 1000, 1), "kN", note=f"{d:g} mm pins, {lo.pin_spacing:g} mm apart"),
        Check(grp, "pin shear stress (double shear)", round(tau, 1), "MPa",
              round(0.577 * lo.pin_yield_mpa / ld.safety_factor), "<=", 0.1),
        Check(grp, f"ear bearing stress ({t:g} mm ears)", round(sig_b, 1), "MPa",
              round(1.5 * lo.ear_yield_mpa / ld.safety_factor), "<=", 0.1),
        Check(grp, "spherical bearing static load vs C0", round(F_pin / 1000, 1), "kN",
              round(lo.bearing_static_kn / 2), "<=", note="GE25ES-class C0 with a factor of 2"),
    )
    r.values.update(M_steer=M_req)


def _home_turning_and_steering(p, tr, r, loads):
    f, st = p.steer_axle, p.steering
    front = tr.axle("front")
    L = front.x - tr.axle("rear").x
    d = math.radians(f.max_steer_deg)
    R_in = L / math.tan(d)                                   # rear-axle line to the turn centre, inner side
    R_outer_front = math.hypot(R_in + f.track, L) + f.tire_width / 2
    r.add(Check("Vehicle", f"turning radius, outer front tyre ({f.max_steer_deg:g} deg inner lock)",
                round(R_outer_front / 1000, 2), "m", note="Ackermann; turn centre on the rear-axle line"))

    grp = "Steering"
    N_wheel = loads["front"] / 2
    M_king = st.scrub_coefficient * N_wheel * (f.tire_width / 3 + f.scrub_radius) / 1000     # per wheel, standstill
    ratio = f.turns_lock_to_lock * 360 / (2 * f.max_steer_deg)                            # handwheel deg per wheel deg
    T_wheel = 2 * M_king / (ratio * 0.75)
    F_rim = T_wheel / (st.steering_wheel_diameter / 2000)
    r.add(
        Check(grp, "front axle load (with operator)", round(loads["front"]), "N",
              note="light front = easy steering, but too light loses steering on climbs"),
        Check(grp, "overall steering ratio", round(ratio, 1), ":1", note=f"{f.turns_lock_to_lock:g} turns lock to lock (REF)"),
        Check(grp, "rim force to steer at standstill", round(F_rim), "N",
              note="estimate: tyre scrub over contact patch + scrub radius, 75 % gear efficiency"),
    )
    climb = tr.axle_loads_n(p.vehicle.max_slope_deg)["front"]
    r.add(Check(grp, f"front axle load climbing {p.vehicle.max_slope_deg:g} deg, share of weight",
                round(climb / (tr.mass() * 9.81) * 100), "%", 15, ">=", 0.2,
                note="below ~15 % the front tyres stop steering (rule of thumb) and the machine can rear up"))
