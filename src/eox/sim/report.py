"""Course results as text: the markdown report and one-line cell summaries."""

from __future__ import annotations

from datetime import date

from eox.sim.run import ObstacleResult, RunResult

STATUSES = ("FAIL", "WARN", "PASS", "INFO")


def headline(o: ObstacleResult) -> str:
    """The one thing to know about an obstacle, short enough for a figure cell."""
    if o.outcome != "cleared":
        return o.outcome
    if o.warnings:
        return o.warnings[0]
    if o.kind == "ramp":
        return f"motor {o.peak_torque_x:.1f}x rated"
    if o.kind == "side_slope":
        return f"lightest wheel {o.min_wheel_n:.0f} N"
    if o.kind == "twist":
        j = o.joint_extremes
        return f"trunnion {j['trunnion']:.0f} deg" if "trunnion" in j else f"axle roll {j.get('axle_roll', 0):.0f} deg"
    return f"pitch {o.max_pitch:.0f} deg"


def counts(r: RunResult) -> dict[str, int]:
    return {s: sum(o.status == s for o in r.obstacles) for s in STATUSES}


def _row(o: ObstacleResult) -> str:
    joints = ", ".join(f"{k} {v:.0f}{' mm' if k == 'bounce' else ' deg'}" for k, v in o.joint_extremes.items())
    deck = "" if o.deck_min_mm == float("inf") else f"{o.deck_min_mm:.0f}"
    notes = "; ".join(o.warnings) or ("beyond the rated climb" if not o.rated else "")
    lightest = f"{o.min_wheel_n:.0f} ({o.min_wheel.replace('_', ' ')})" if o.min_wheel else ""
    return (f"| {o.status} | {o.name} | {o.outcome} | {o.max_roll:.1f} / {o.max_pitch:.1f} | {lightest} | "
            f"{o.peak_torque_x:.1f}x | {o.max_slip:.0f} | {deck} | {joints} | {notes} |")


def markdown(p, results: list[RunResult], course) -> str:
    import mujoco
    v = p.vehicle
    lines = [
        f"# {p.model.name} on the {course.name}", "",
        f"Generated {date.today().isoformat()} by `uv run eox course --model {p.model.name.split()[-1].lower()}`: "
        f"a MuJoCo {mujoco.__version__} rigid-body simulation of the same masses and part envelopes the calcs use "
        "(`src/eox/sim/`). Screening level: rigid tyres, REF spring and friction values.", "",
        f"**Course:** {course.length:.1f} m, {len(course.segments)} obstacles, driven at {p.course.speed_kmh:g} km/h; "
        f"level of detail {p.course.lod}  ",
        f"**Ground:** {p.ground.name}, cone index {p.ground.cone_index_kpa:g} kPa; tyre grip and rolling resistance "
        f"follow each wheel's load (at rest: traction {v.traction_coefficient:.2f}, rolling resistance "
        f"{v.rolling_resistance:.3f})  ",
        f"**Rated climb:** {v.max_slope_deg:g} deg (steeper ramps are scored INFO)", "",
        "Columns: roll / pitch are the worst body angles (deg). The lightest wheel load is averaged over 0.2 s (N). "
        "Motor is the worst drive unit's torque as a multiple of rated (peak is about 4x). "
        "Deck is the rigidly mounted deck's lowest clearance (mm; negative = it would dig in, so its hitch must "
        f"float that far; {p.course.scoring.deck_float:g} mm allowed).", "",
    ]
    for r in results:
        c = counts(r)
        lines += [f"## {r.config.capitalize()}", "",
                  f"{'Finished' if r.completed else 'Did not finish'} in {r.time_s:.0f} s, "
                  f"{r.energy_wh:.1f} Wh at the wheels"
                  + (f", helped past {r.recoveries} obstacle(s)" if r.recoveries else "") + ". "
                  + f"**{c['FAIL']} FAIL, {c['WARN']} WARN, {c['PASS']} PASS, {c['INFO']} INFO**", "",
                  "| | Obstacle | Outcome | Roll / pitch | Lightest wheel | Motor | Slip % | Deck | Joints | Notes |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        lines += [_row(o) for o in r.obstacles] + [""]
    return "\n".join(lines) + "\n"
