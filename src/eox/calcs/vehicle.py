"""Whole-machine checks: mass split, static stability, turning, steering
effort, and (Pro) the articulation joint's clearances."""

from __future__ import annotations

import math

import numpy as np

from eox.calcs.common import Report
from eox.checks import Check
from eox.tractor import DECK, HALVES

CONFIGS = ((), DECK)            # bare, and mowing with the deck fitted: every check takes the worse


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


def stability(tr, gamma: float = 0.0, fitted: tuple = ()) -> dict[str, float]:
    """Tip angles. rigid: all four wheels, whole-machine CG.
    Pro only, front/rear: each half's stability triangle (its two wheels + the
    pivot). The pivot locks pitch, so a half can only tip sideways, about the
    lines from its wheels to the pivot, never back over its own axle."""
    four = tr.contacts("front", gamma) + tr.contacts("rear", gamma)
    out = {"rigid": tip_angle(tr.cg(None, gamma, fitted), _ring(four))}
    if tr.articulated:
        j = tr.joint()
        for half in HALVES:
            left, right = tr.contacts(half, gamma)
            out[half] = tip_angle(tr.cg(half, gamma, fitted), [(left, j), (right, j)])
    elif getattr(tr.p.steer_axle, "oscillates", False):
        f = tr.axle("front")
        pivot = (f.x, 0.0, f.tire_diameter / 2)
        out["triangle"] = tip_angle(tr.cg(fitted=fitted), _ring(tr.contacts("rear") + [pivot]))
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
                                   ("steering", "frame"), ("implement", "frame"), ("controller", "frame"),
                                   ("deck", "pto"), ("deck", "implement"))}


def steer_sweep_hits(tr, step_deg: float = 2.5) -> list[str]:
    """Home: parts inside the volume the steered front tyres sweep, lock to
    lock. Each tyre's plan footprint turns about its kingpin (inboard of the
    tyre centre by the scrub radius) and stands one tyre diameter tall. The
    axle, its rack and the wheels themselves are meant to be there."""
    from eox.powerbox import Body

    f = tr.p.steer_axle
    ax = tr.axle("front")
    hl, hw = ax.tire_diameter / 2, ax.tire_width / 2
    L, W, H = tr.box.outer
    bx, _, bz = tr.box_pos
    items = [b for g, k, b in tr.bodies if k not in ("wheel", "axle", "steering", "deck", "pto")]
    items.append(Body("power box", "box", (bx, 0, bz + H / 2), (L, W, H)))
    feet = []
    n = int(2 * f.max_steer_deg / step_deg) + 1
    for side in (1, -1):
        ky = side * (ax.track / 2 - f.scrub_radius)
        for i in range(n):
            g = math.radians(-f.max_steer_deg + i * step_deg)
            pts = [(dx, side * f.scrub_radius + dy) for dx, dy in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]
            feet.append([(ax.x + x * math.cos(g) - y * math.sin(g), ky + x * math.sin(g) + y * math.cos(g)) for x, y in pts])
    hits = []
    for b in items:
        z0 = b.bounds()[4]
        if z0 >= ax.tire_diameter + 20:
            continue
        rect = _plan_rect(b)
        if any(_overlap(rect, foot) for foot in feet):
            hits.append(b.name)
    # the steering column runs from the rack up to the wheel: it must pass clear of the box
    x0, x1, y0, y1, z0, z1 = items[-1].bounds()
    for ln in tr.links:
        r_ = ln.diameter / 2
        for i in range(21):
            q = [ln.a[k] + (ln.b[k] - ln.a[k]) * i / 20 for k in range(3)]
            if x0 - r_ < q[0] < x1 + r_ and y0 - r_ < q[1] < y1 + r_ and z0 - r_ < q[2] < z1 + r_:
                hits.append(f"{ln.name} / power box")
                break
    return hits


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
    people = v.mass_operator_kg + v.mass_payload_kg
    grp = "Vehicle"
    r.add(Check(grp, "machine mass (no operator): bare / deck fitted",
                " / ".join(f"{tr.mass(fitted=f) - people:.0f}" for f in CONFIGS), "kg",
                note=f"deck {p.deck.mass_kg:g} kg + its PTO unit, mount = {p.deck.mount}"))
    if tr.articulated:
        r.add(Check(grp, "mass with operator, front / rear half: bare; deck fitted",
                    "; ".join(f"{tr.mass('front', f):.0f} / {tr.mass('rear', f):.0f}" for f in CONFIGS), "kg"))
    splits, cgs = [], []
    for f in CONFIGS:
        ld = tr.axle_loads_n(fitted=f)
        splits.append(f"{ld['front'] / (ld['front'] + ld['rear']) * 100:.0f} / {ld['rear'] / (ld['front'] + ld['rear']) * 100:.0f}")
        c = tr.cg(fitted=f)
        cgs.append(f"{c[0]:.0f} / {c[1]:.0f} / {c[2]:.0f}")
    r.add(
        Check(grp, "axle load split front / rear (with operator): bare; deck fitted", "; ".join(splits), "%"),
        Check(grp, "CG x / y / z (with operator): bare; deck fitted", "; ".join(cgs), "mm",
              note="origin on the ground under the pivot" if tr.articulated else "origin on the ground under the rear axle"),
    )
    if tr.articulated:
        _pro_turning_and_steering(p, tr, r)
    else:
        _home_turning_and_steering(p, tr, r)
    hits = parts_overlap(tr)
    r.add(Check(grp, "major parts clear each other (power box, units, axles, seat, frame)", len(hits), "overlaps", 0, "<=",
                note="; ".join(hits) if hits else "box outlines within each rigid group"))
    L, _, _ = tr.box.outer
    rails = [b.bounds() for g, k, b in tr.bodies if g == tr.box_group and k == "frame"
             and b.name not in ("floor pan", "footrest", "seat pedestal", "seat post L", "seat post R", "box stand")]
    past = max(min(r_[0] for r_ in rails) - (tr.box_pos[0] - L / 2), (tr.box_pos[0] + L / 2) - max(r_[1] for r_ in rails), 0)
    r.add(Check(grp, "power box sits within the frame (fore-aft)", round(past), "mm past the frame", 50, "<=",
                note="the box (or its stand) must bear on the rails, not hang off the end"))

    # ---- stability ------------------------------------------------------------------
    grp = "Stability"
    angles = [0.0] + ([p.layout.articulation_max_deg] if tr.articulated else [])
    worst = 90.0
    for gamma in angles:
        runs = [stability(tr, gamma, f) for f in CONFIGS]           # bare and deck fitted
        s = {k: min(run_[k] for run_ in runs) for k in runs[0]}
        worst = min(worst, *s.values())
        label = "straight" if not gamma else f"articulated {gamma:g} deg"
        if tr.articulated:
            r.add(Check(grp, f"tip angle, {label}: rigid / front half / rear half",
                        f"{s['rigid']:.0f} / {s['front']:.0f} / {s['rear']:.0f}", "deg",
                        note="worst slope direction, bare or deck fitted; a half starts to roll onto its oscillation stop at its own angle"))
        else:
            r.add(Check(grp, "tip angle, four wheels" + (" / front-axle triangle" if "triangle" in s else ""),
                        " / ".join(f"{s[k]:.0f}" for k in s), "deg", note="worst slope direction, bare or deck fitted"))
    r.add(Check(grp, "max working slope (half the lowest tip angle)", round(worst / 2, 1), "deg",
                v.design_slope_deg, ">=", warn_limit=v.max_slope_deg,
                note="industry practice, not a confirmed standard value: B71.1 stability numbers still to verify"))

    # ---- deck mounting (open decision, issue 7) ---------------------------------------
    d, front = p.deck, tr.axle("front")
    note = ("the front axle must roll over the deck: negative means it can't" if d.mount.startswith("mid")
            else "the deck couples to the implement face and never passes under an axle: reference only")
    r.add(Check("Deck", "drive-over: front axle clearance minus deck top at min cut",
                front.clearance - d.top_height_min_cut, "mm", note=f"mount = {d.mount}; {note}"))
    r.values.update(worst_tip=worst)


def _pro_turning_and_steering(p, tr, r):
    lo, a, st = p.layout, p.axle, p.steering
    gmax = math.radians(lo.articulation_max_deg)
    af, ar = lo.front_axle_x, -lo.rear_axle_x
    R = max((af * math.cos(gmax) + ar) / math.sin(gmax), (ar * math.cos(gmax) + af) / math.sin(gmax))
    r.add(Check("Vehicle", f"turning radius, outer tyre at {lo.articulation_max_deg:g} deg",
                round((R + a.track / 2 + a.tire_width / 2) / 1000, 2), "m",
                note="articulated: both axles track the same arc when a = b"))

    grp = "Steering"
    M_f = M_r = 0.0
    for f in CONFIGS:                                            # the heavier configuration sets the moment
        ld = tr.axle_loads_n(fitted=f)
        M_f = max(M_f, st.scrub_coefficient * ld["front"] * af / 1000)
        M_r = max(M_r, st.scrub_coefficient * ld["rear"] * ar / 1000)
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
    M_pitch = F_pin = 0.0
    for f in CONFIGS:
        W_r = tr.mass("rear", f) * g0
        x_rc = tr.cg("rear", fitted=f)[0]
        N_r = tr.axle_loads_n(fitted=f)["rear"]
        m = abs(W_r * x_rc - N_r * lo.rear_axle_x)                          # N*mm
        F = math.hypot(ld.vertical_g * m / lo.pin_spacing + ld.longitudinal_g * W_r / 2, ld.lateral_g * W_r / 2)
        M_pitch, F_pin = max(M_pitch, m), max(F_pin, F)
    d, t = lo.pin_diameter, lo.ear_thickness
    tau = F_pin / (2 * math.pi * d * d / 4)                                  # double shear
    sig_b = F_pin / (2 * d * t)                                              # two ears per pin
    r.add(
        Check(grp, "pitch moment through the joint (static)", round(M_pitch / 1000), "N*m",
              note="the pivot locks pitch, so the halves share it; taken by the pin couple (worse of bare / deck)"),
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


def _home_turning_and_steering(p, tr, r):
    f, st = p.steer_axle, p.steering
    front = tr.axle("front")
    L = front.x - tr.axle("rear").x
    d = math.radians(f.max_steer_deg)
    R_in = L / math.tan(d)                                   # rear-axle line to the turn centre, inner side
    R_outer_front = math.hypot(R_in + f.track, L) + f.tire_width / 2
    r.add(Check("Vehicle", f"turning radius, outer front tyre ({f.max_steer_deg:g} deg inner lock)",
                round(R_outer_front / 1000, 2), "m", note="Ackermann; turn centre on the rear-axle line"))

    hits = steer_sweep_hits(tr)
    r.add(Check("Vehicle", f"steered front tyres clear every part, lock to lock (+-{f.max_steer_deg:g} deg)", len(hits),
                "hits", 0, "<=", note=", ".join(hits) or "plan sweep about the kingpins, one tyre diameter tall"))

    grp = "Steering"
    loads = max((tr.axle_loads_n(fitted=f) for f in CONFIGS), key=lambda ld: ld["front"])   # heavier front steers harder
    N_wheel = loads["front"] / 2
    M_king = st.scrub_coefficient * N_wheel * (f.tire_width / 3 + f.scrub_radius) / 1000     # per wheel, standstill
    ratio = f.turns_lock_to_lock * 360 / (2 * f.max_steer_deg)                            # handwheel deg per wheel deg
    T_wheel = 2 * M_king / (ratio * 0.75)
    F_rim = T_wheel / (st.steering_wheel_diameter / 2000)
    r.add(
        Check(grp, "front axle load (with operator, heavier configuration)", round(loads["front"]), "N",
              note="light front = easy steering, but too light loses steering on climbs"),
        Check(grp, "overall steering ratio", round(ratio, 1), ":1", note=f"{f.turns_lock_to_lock:g} turns lock to lock (REF)"),
        Check(grp, "rim force to steer at standstill", round(F_rim), "N",
              note="estimate: tyre scrub over contact patch + scrub radius, 75 % gear efficiency"),
    )
    share = min(tr.axle_loads_n(p.vehicle.max_slope_deg, f)["front"] / (tr.mass(fitted=f) * 9.81) for f in CONFIGS)
    r.add(Check(grp, f"front axle load climbing {p.vehicle.max_slope_deg:g} deg, share of weight",
                round(share * 100), "%", 15, ">=", 0.2,
                note="below ~15 % the front tyres stop steering (rule of thumb) and the machine can rear up"))
