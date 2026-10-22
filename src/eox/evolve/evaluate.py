"""Score one design: the calcs, the BOM and the terrain course, as named metrics.

A design is a model plus a set of genes (dotted design values, the same keys
an [overrides] table takes). Everything is computed from scratch by the same
code `eox calc`, `eox bom` and `eox course` run, so a trial can't score a
design differently from the way the repo checks it.
"""

from __future__ import annotations

import time

# metric -> (unit, what it measures). Objectives and constraints name these.
METRICS = {
    "calc_fails": ("", "engineering checks that FAIL"),
    "calc_warns": ("", "engineering checks that WARN"),
    "course_fails": ("", "course obstacles that FAIL (stuck, rolled, left the course)"),
    "course_warns": ("", "course obstacles that WARN"),
    "wheel_lift_s": ("s", "longest wheel lift, summed over the obstacles"),
    "deck_float_mm": ("mm", "float the deck's hitch needs (worst obstacle)"),
    "side_slope_wheel_n": ("N", "lightest wheel load on the side slope"),
    "course_peak_torque_s": ("s", "time a drive unit sat at its torque limit"),
    "course_energy_wh": ("Wh", "drive energy for the course"),
    "mass_kg": ("kg", "machine mass with the deck, no operator"),
    "cost_usd": ("$", "purchased parts, budgetary"),
    "mowing_runtime_h": ("h", "runtime on one charge, mowing"),
    "working_slope_deg": ("deg", "max working slope (half the lowest static tip angle)"),
    "grip_limit_deg": ("deg", "steepest climb on grip, deck fitted"),
    "rated_slope_deg": ("deg", "rated climb (vehicle.max_slope_deg)"),
    "climb_torque_x": ("x rated", "motor torque on the rated climb, deck fitted"),
    "steer_margin": ("", "Pro: cylinder moment at full lock over the moment needed, minus 1"),
    "lock_to_lock_s": ("s", "Pro: steering lock-to-lock time"),
    "steer_rim_n": ("N", "Home: rim force to steer at a standstill"),
    "steer_bore_mm": ("mm", "Pro: steering cylinder bore (a proxy for its size and cost)"),
    "steer_pump_w": ("W", "Pro: steering power unit's average draw while working"),
}

BOX_SECTIONS = ("meta", "battery", "enclosure", "distribution", "battery_clamp", "battery_stop")
_boxes: dict = {}


def _box(p):
    """The power box is the slow part to build (CAD solids). Reuse it while
    the genes leave its sections alone."""
    from eox import powerbox
    key = repr([getattr(p, s) for s in BOX_SECTIONS])
    if key not in _boxes:
        _boxes[key] = powerbox.build(p)
    return _boxes[key]


def _check(rep, prefix, group=None):
    return next(c for c in rep.checks if c.name.startswith(prefix) and (group is None or c.group == group))


def evaluate(model: str, genes: dict, course_configs: tuple = ("deck",)) -> dict:
    """All METRICS for one design, plus the names of what failed or warned.
    A design that can't be built or checked comes back with an "error"."""
    from eox import bom, calcs, tractor
    from eox.calcs.drive import _per_motor
    from eox.params import load
    from eox.sim import run as sim
    from eox.tractor import DECK

    t0 = time.time()
    try:
        p = load(model, genes)
        tr = tractor.build(p, _box(p))
        rep = calcs.run(p, tr)
        _, tot = bom.rollup(p, tr.box)
        u, v = p.unit, p.vehicle
        T_rated = u.rated_power_w / (2 * 3.141592653589793 * u.base_speed_rpm / 60)
        m = {
            "calc_fails": sum(c.status == "FAIL" for c in rep.checks),
            "calc_warns": sum(c.status == "WARN" for c in rep.checks),
            "mass_kg": tr.mass(fitted=DECK) - v.mass_operator_kg - v.mass_payload_kg,
            "cost_usd": tot["total"]["usd"],
            "mowing_runtime_h": float(_check(rep, "runtime on one charge", "Mode mowing").value),
            "working_slope_deg": float(_check(rep, "max working slope").value),
            "grip_limit_deg": float(_check(rep, "steepest climb on grip").value),
            "rated_slope_deg": float(v.max_slope_deg),
            "climb_torque_x": _per_motor(p, tr, v.max_slope_deg) / T_rated,
        }
        cyl = next((c for c in rep.checks if c.name.startswith("cylinder moment at full lock")), None)
        ltl = next((c for c in rep.checks if c.name.startswith("lock-to-lock time")), None)
        rim = next((c for c in rep.checks if c.name.startswith("rim force to steer")), None)
        from eox.calcs.bus import steering_pump_w
        hyd = getattr(p.steering, "type", "").startswith("hydraulic")
        m.update(steer_margin=(cyl.value / cyl.limit - 1) if cyl else 0.0, lock_to_lock_s=float(ltl.value) if ltl else 0.0,
                 steer_rim_n=float(rim.value) if rim else 0.0, steer_bore_mm=float(p.steering.bore) if hyd else 0.0,
                 steer_pump_w=float(steering_pump_w(p)))
        notes = [f"{c.group}: {c.name}" for c in rep.checks if c.status == "FAIL"]
        warn_notes = []
        course = dict(course_fails=0, course_warns=0, wheel_lift_s=0.0, deck_float_mm=0.0,
                      side_slope_wheel_n=float("inf"), course_peak_torque_s=0.0, course_energy_wh=0.0)
        for cfg in course_configs:
            r = sim.run(p, tr, DECK if cfg == "deck" else (), keep_trajectory=False)
            course["course_energy_wh"] += r.energy_wh
            for o in r.obstacles:
                if not o.rated:                              # a climb beyond this design's rating: not scored
                    continue
                course["course_fails"] += o.status == "FAIL"
                course["course_warns"] += o.status == "WARN"
                course["wheel_lift_s"] += o.lift_s
                course["course_peak_torque_s"] += o.at_peak_s
                if o.deck_min_mm < 0:
                    course["deck_float_mm"] = max(course["deck_float_mm"], -o.deck_min_mm)
                if o.kind == "side_slope":
                    course["side_slope_wheel_n"] = min(course["side_slope_wheel_n"], o.min_wheel_n)
                if o.status == "FAIL":
                    notes.append(f"course {cfg}: {o.name} {o.outcome}")
                elif o.status == "WARN":
                    warn_notes.append(f"{cfg} {o.name}: " + "; ".join(o.warnings))
        if course["side_slope_wheel_n"] == float("inf"):
            course["side_slope_wheel_n"] = 0.0
        m.update(course)
        return {"metrics": {k: round(float(x), 4) for k, x in m.items()}, "fails": notes, "warns": warn_notes,
                "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:                                   # a gene combination that can't be built
        return {"error": f"{type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 1)}
