"""Reference machines: real lawn tractors and riders, modelled from their
published specs, so EOX designs can be baselined against what real products
do on the same checks and the same terrain course.

A reference is design/reference/<name>.toml. It holds what the maker
publishes (mass, wheelbase, tracks, tyres, rated slope, axle torque) and,
marked REF, what they don't (weight split, CG height). Bodies are simple
envelopes; masses are a few lumps placed to match the published mass and
the estimated weight split and CG height. That is coarse, but it puts the
real wheelbase, track, tyres, axle pivot, drive torque and deck clearance on
the course, which is what the course tests.

Layouts:
  lawn_tractor      engine in front, rear transaxle (open diff), pivoting
                    front axle, mid-mount deck (Deere, Cub Cadet, Ryobi)
  articulated_rider front deck, centre pivot, engine behind the rear axle,
                    AWD optional (Husqvarna R-series)
"""

from __future__ import annotations

import math
import tomllib

from eox.params import DESIGN, _ns
from eox.tractor import Axle, Link, Mass, Tractor, _Builder

REFERENCE = DESIGN / "reference"
NAMES = tuple(sorted(f.stem for f in REFERENCE.glob("*.toml"))) if REFERENCE.exists() else ()


def load(name: str):
    path = REFERENCE / f"{name}.toml"
    if not path.exists():
        raise FileNotFoundError(f"design/reference/{name}.toml (references: {', '.join(NAMES)})")
    merged = {}
    for shared in ("course", "ground"):
        with open(DESIGN / f"{shared}.toml", "rb") as f:
            merged.update(tomllib.load(f))
    with open(path, "rb") as f:
        merged.update(tomllib.load(f))
    return _ns(merged)


def _solve_lumps(known: list[Mass], m_rest: float, x_target_m: float, xs: tuple[float, float]) -> tuple[float, float]:
    """Split m_rest between two lumps at xs so the whole machine's CG lands at x_target."""
    M = sum(k.kg for k in known) + m_rest
    need = x_target_m * M - sum(k.kg * k.cg[0] for k in known)
    x1, x2 = xs
    m1 = (need - m_rest * x2) / (x1 - x2)
    m1 = min(max(m1, 0.0), m_rest)
    return m1, m_rest - m1


def _place_z(tr: Tractor, lumps: list[str], cg_height: float, fitted) -> None:
    """Raise or lower the named lumps together so the machine (no operator) has the given CG height."""
    ms = [m for m in tr._counted(None, fitted) if m.name != "operator"]
    M = sum(m.kg for m in ms)
    fixed = sum(m.kg * m.cg[2] for m in ms if m.name not in lumps)
    lk = sum(m.kg for m in ms if m.name in lumps)
    z = (cg_height * M - fixed) / lk if lk else 0.0
    for m in tr.masses:
        if m.name in lumps:
            m.cg = (m.cg[0], m.cg[1], z)


def build_lawn_tractor(p) -> Tractor:
    s, e, f = p.spec, p.estimate, p.steer_axle
    tr = Tractor(p, None, (0.0, 0.0, 0.0), "chassis", articulated=False)
    B = _Builder(tr)
    L = s.wheelbase
    rd, rw = s.rear_tire
    fd, fw = s.front_tire
    rr, fr = rd / 2, fd / 2
    clr = s.ground_clearance
    # wheels and axles
    for side, nm in ((1, "L"), (-1, "R")):
        B.add("chassis", "wheel", f"wheel {nm}", "cyl_y", (0, side * s.rear_track / 2, rr), (rd, rw), e.rear_wheel_kg)
        B.add("chassis", "wheel", f"front wheel {nm}", "cyl_y", (L, side * f.track / 2, fr), (fd, fw), e.front_wheel_kg)
    B.add("chassis", "axle", "rear end", "box", (0, 0, rr), (220, 260, 2 * (rr - e.transaxle_clearance)))
    tr.axles.append(Axle("rear", 0.0, s.rear_track, rd, rw, "chassis", True, e.transaxle_clearance,
                         s.rear_tire_rim, s.rear_tire_pressure_kpa))
    B.add("chassis", "axle", "front beam axle", "box", (L, 0, fr), (60, f.track - fw, 2 * (fr - f.beam_clearance)),
          e.front_axle_kg)
    tr.axles.append(Axle("front", L, f.track, fd, fw, "chassis", False, f.beam_clearance,
                         s.front_tire_rim, s.front_tire_pressure_kpa))
    # body envelopes: frame, hood over the engine, rear body / fenders under the seat
    rail_z = clr + 40
    for side in (1, -1):              # low between the axles; the nose and tail sit higher, as real frames do
        sd = "L" if side > 0 else "R"
        B.add("chassis", "frame", f"rail {sd}", "box", (L / 2 - 100, side * e.frame_half_width, rail_z), (L - 200, 40, 80))
        B.add("chassis", "frame", f"nose {sd}", "box", (L - 100 + (e.front_overhang + 100) / 2, side * e.frame_half_width,
                                                        e.nose_clearance + 40), (e.front_overhang + 100, 40, 80))
        B.add("chassis", "frame", f"tail {sd}", "box", (-100 - (e.rear_overhang - 100) / 2, side * e.frame_half_width,
                                                        e.tail_clearance + 40), (e.rear_overhang - 100, 40, 80))
    hood_x0, hood_x1 = L - 450, L + e.front_overhang                       # hood: from the dash to the nose
    hz = e.nose_clearance + 80
    B.add("chassis", "frame", "hood", "box", ((hood_x0 + hood_x1) / 2, 0, (hz + e.hood_top) / 2),
          (hood_x1 - hood_x0, e.hood_width, e.hood_top - hz))
    body_x0, body_x1 = -e.rear_overhang, e.seat_x + 200                     # rear body: tail to under the seat
    bz = e.tail_clearance + 80
    B.add("chassis", "frame", "rear body", "box", ((body_x0 + body_x1) / 2, 0, (bz + e.seat_height) / 2),
          (body_x1 - body_x0, e.frame_half_width * 2 + 120, e.seat_height - bz))
    B.add("chassis", "seat", "seat", "box", (e.seat_x, 0, e.seat_height + 60), (420, 440, 120))
    # deck: mid-mount, tagged so "bare" leaves it off
    dz = e.deck_bottom_clearance + e.deck_height / 2
    B.add("chassis", "deck", "mower deck", "box", (e.deck_x, 0, dz), (e.deck_length, s.deck_width, e.deck_height),
          e.deck_mass_kg, tag="deck")
    # two lumps (engine + hood at the front; transaxle, fuel/battery, rear body at the back) fixed by
    # the published mass and the estimated weight split, then raised to the estimated CG height
    known = [m for m in tr.masses]
    m_rest = s.mass_kg - sum(m.kg for m in known)
    mf, mr = _solve_lumps(known, m_rest, e.front_share * L, (L + e.engine_x_from_front_axle, e.rear_lump_x))
    B.mass("chassis", "engine and front body", mf, (L + e.engine_x_from_front_axle, 0, 400))
    B.mass("chassis", "transaxle and rear body", mr, (e.rear_lump_x, 0, 400))
    _place_z(tr, ["engine and front body", "transaxle and rear body"], e.cg_height, ("deck",))
    tr.links.append(Link("steering column", "seat", (L - 150, 0, rail_z + 40), "chassis",
                         (e.seat_x + 480, 0, e.seat_height + 300), "chassis", 25))
    B.mass("chassis", "operator", p.vehicle.mass_operator_kg, (e.seat_x, 0, e.seat_height + 250))
    return tr


def build_articulated_rider(p) -> Tractor:
    s, e, lo = p.spec, p.estimate, p.layout
    tr = Tractor(p, None, (0.0, 0.0, 0.0), "front", articulated=True)
    B = _Builder(tr)
    rd, rw = s.rear_tire
    fd, fw = s.front_tire
    clr = s.ground_clearance
    rail_z = clr + 40
    for group, x, tire, track, driven in (("rear", lo.rear_axle_x, s.rear_tire, s.rear_track, True),
                                          ("front", lo.front_axle_x, s.front_tire, s.front_track, e.awd)):
        d, w = tire
        for side, nm in ((1, "L"), (-1, "R")):
            B.add(group, "wheel", f"wheel {nm}", "cyl_y", (x, side * track / 2, d / 2), (d, w),
                  e.rear_wheel_kg if group == "rear" else e.front_wheel_kg)
        B.add(group, "axle", "rear end", "box", (x, 0, d / 2), (200, 240, 2 * (d / 2 - e.axle_clearance)))
        tr.axles.append(Axle(group, x, track, d, w, group, driven, e.axle_clearance,
                             getattr(s, f"{group}_tire_rim"), getattr(s, f"{group}_tire_pressure_kpa")))
        sgn = 1 if group == "front" else -1
        end_z = (e.nose_clearance if group == "front" else e.tail_clearance) + 40
        for side in (1, -1):
            sd = "L" if side > 0 else "R"
            B.add(group, "frame", f"rail {sd}", "box", ((sgn * 120 + x) / 2, side * e.frame_half_width, rail_z),
                  (abs(x - sgn * 120), 40, 80))
            B.add(group, "frame", f"end {sd}", "box", (x + sgn * e.overhang / 2, side * e.frame_half_width, end_z),
                  (e.overhang, 40, 80))
    ph = lo.pivot_height
    B.add("rear", "pivot", "knuckle", "box", (-40, 0, ph), (80, 80, 120), e.knuckle_kg)
    hz = e.tail_clearance + 80
    B.add("rear", "frame", "engine hood", "box", (lo.rear_axle_x - e.overhang / 2, 0, (hz + e.hood_top) / 2),
          (e.overhang + 200, e.hood_width, e.hood_top - hz))
    B.add("rear", "seat", "seat", "box", (e.seat_x, 0, e.seat_height + 60), (420, 440, 120))
    # front-mount deck ahead of the front axle
    dz = e.deck_bottom_clearance + e.deck_height / 2
    B.add("front", "deck", "mower deck", "box", (e.deck_x, 0, dz), (e.deck_length, s.deck_width, e.deck_height),
          e.deck_mass_kg, tag="deck")
    known = [m for m in tr.masses]
    m_rest = s.mass_kg - sum(m.kg for m in known)
    mf, mr = _solve_lumps(known, m_rest, e.front_share * (lo.front_axle_x - lo.rear_axle_x) + lo.rear_axle_x,
                          (lo.front_axle_x, lo.rear_axle_x - e.overhang * 0.6))
    B.mass("front", "front frame and axle", mf, (lo.front_axle_x, 0, 350))
    B.mass("rear", "engine and rear frame", mr, (lo.rear_axle_x - e.overhang * 0.6, 0, 350))
    _place_z(tr, ["front frame and axle", "engine and rear frame"], e.cg_height, ("deck",))
    B.mass("rear", "operator", p.vehicle.mass_operator_kg, (e.seat_x, 0, e.seat_height + 250))
    return tr


BUILDERS = {"lawn_tractor": build_lawn_tractor, "articulated_rider": build_articulated_rider}
MARGIN = 1.2


def build(p) -> Tractor:
    """The machine, and its drive's peak axle torque. Transaxle makers publish a
    rated (continuous) axle torque; the hydrostatic relief allows more. The
    maker rates the machine for its slope, so the model gets at least the
    torque to climb that slope with the operator and deck, plus 20 %."""
    from eox.calcs.common import tractive_force
    from eox.tractor import DECK

    from eox import tyres
    tr = BUILDERS[p.model.layout](p)
    tyres.apply(p, tr)
    d = p.drive
    driven = [ax for ax in tr.axles if ax.driven]
    r = driven[0].tire_diameter / 2000
    need = tractive_force(tr.mass(fitted=DECK), p.vehicle.max_slope_deg, p.vehicle.rolling_resistance) * r / len(driven)
    d.axle_torque_nm = max(getattr(d, "rated_axle_torque_nm", 0.0), MARGIN * need)
    if hasattr(d, "front_rated_axle_torque_nm"):
        d.front_axle_torque_nm = max(d.front_rated_axle_torque_nm, MARGIN * need)
    d.from_rating = d.axle_torque_nm > getattr(d, "rated_axle_torque_nm", 0.0)
    return tr


def evaluate(name: str, configs: tuple = ("deck",)) -> dict:
    """The comparable metrics for a reference machine: static stability and
    grip as the EOX calcs compute them, and the terrain course."""
    from eox.calcs.drive import grip_limit
    from eox.calcs.vehicle import stability
    from eox.sim import run as sim
    from eox.tractor import DECK

    p = load(name)
    tr = build(p)
    v = p.vehicle
    angles = [0.0] + ([p.layout.articulation_max_deg] if tr.articulated else [])
    worst = min(x for g in angles for x in stability(tr, g, DECK).values())   # as sold for mowing: deck fitted
    m = {"mass_kg": tr.mass(fitted=DECK) - v.mass_operator_kg - v.mass_payload_kg,
         "working_slope_deg": worst / 2, "grip_limit_deg": grip_limit(p, tr, DECK),
         "rated_slope_deg": float(v.max_slope_deg), "cost_usd": float(p.spec.price_usd),
         "front_share_pct": 100 * tr.axle_loads_n(fitted=DECK)["front"] / (tr.mass(fitted=DECK) * 9.81)}
    runs = [sim.run(p, tr, DECK if c == "deck" else (), keep_trajectory=False) for c in configs]
    return {"name": p.model.name, "kind": p.model.kind, "metrics": m, "runs": runs, "p": p, "tr": tr}
