"""Drive: golf-cart axle modules, one 3 HP unit each.

Per-motor torque = (tractive force / driven axles) x tire radius / (ratio x
efficiency). Torque at or under the unit's rated torque is continuous duty;
up to its peak is short-time duty (motor heats); past the peak it can't climb.
"""

from __future__ import annotations

import math

from eox.calcs.bus import drivetrain_efficiency
from eox.calcs.common import G0, Report, tractive_force
from eox.checks import Check


def _per_motor(p, tr, slope_deg: float, extra: float | None = None) -> float:
    a = p.axle
    extra = a.extra_reduction if extra is None else extra
    eta = a.efficiency * (0.97 if extra > 1 else 1.0)
    F = tractive_force(tr.mass(), slope_deg, p.vehicle.rolling_resistance)
    return F / 2 * (a.tire_diameter / 2000) / (a.ratio * extra * eta)


def _motor_rpm(p, kmh: float, extra: float | None = None) -> float:
    a = p.axle
    extra = a.extra_reduction if extra is None else extra
    return kmh / 3.6 / (math.pi * a.tire_diameter / 1000) * 60 * a.ratio * extra


def run(p, tr, r: Report):
    grp = "Drive"
    u, a, v = p.unit, p.axle, p.vehicle
    T_rated = u.rated_power_w / (2 * math.pi * u.base_speed_rpm / 60)
    T_peak = T_rated * u.peak_torque_factor
    T_design = _per_motor(p, tr, v.design_slope_deg)
    T_max = _per_motor(p, tr, v.max_slope_deg)
    n_top = _motor_rpm(p, v.top_speed_kmh)
    n_mow = _motor_rpm(p, p.modes.mowing.drive_speed_kmh)
    ratio = a.ratio * a.extra_reduction
    r.add(
        Check(grp, "overall ratio (rear end x extra stage)", round(ratio, 1), ":1",
              note="stock golf-cart rear end" if a.extra_reduction == 1 else f"{a.extra_reduction:g}:1 stage added"),
        Check(grp, f"motor torque each, {v.design_slope_deg:g} deg climb (sustained)", round(T_design, 1), "N*m",
              round(T_peak, 1), "<=", warn_limit=round(T_rated, 1),
              note=f"{T_design / T_rated:.1f}x rated: over rated = short-time duty, motor heats"),
        Check(grp, f"motor torque each, {v.max_slope_deg:g} deg climb (short)", round(T_max, 1), "N*m",
              round(T_peak, 1), "<=", 0.1, note=f"{T_max / T_rated:.1f}x rated"),
        Check(grp, f"motor speed at {v.top_speed_kmh:g} km/h", round(n_top), "rpm", u.max_speed_rpm, "<=", 0.05),
        Check(grp, "motor speed at mowing pace vs base speed", round(n_mow / u.base_speed_rpm * 100), "%",
              note="self-cooling fan works poorly this slow; watch motor temperature"),
        Check(grp, f"drive power available per unit at {v.top_speed_kmh:g} km/h", round(T_rated * n_top * 2 * math.pi / 60),
              "W", note=f"rated torque x speed, of {u.rated_power_w:.0f} W: the rest of the unit is geared away"),
    )

    # traction vs motor peak: which one limits a hard pull
    W = tr.mass() * G0
    F_motors = 2 * T_peak * a.ratio * a.extra_reduction * drivetrain_efficiency(p) / (a.tire_diameter / 2000)
    F_grip = v.traction_coefficient * W
    r.add(
        Check(grp, "peak tractive force: motors / tyre grip", f"{F_motors:,.0f} / {F_grip:,.0f}", "N",
              note="grip limits first (wheels slip before motors stall)" if F_grip < F_motors
              else "motors limit first"),
        Check(grp, "steepest climb on grip (AWD)", round(math.degrees(math.atan(v.traction_coefficient)) -
              math.degrees(math.atan(v.rolling_resistance)), 1), "deg", note="before rolling resistance cos term; INFO"),
    )

    # gearing options: what an extra reduction stage buys
    for extra in (1.0, 2.0, 3.0):
        t = _per_motor(p, tr, v.design_slope_deg, extra)
        top = u.base_speed_rpm / (a.ratio * extra) * math.pi * a.tire_diameter / 1000 * 60 / 1000
        r.add(Check(grp, f"gearing option {a.ratio * extra:.0f}:1 ({extra:g}x stage)",
                    f"{t / T_rated:.1f}x rated / {top:.0f} km/h", "",
                    note=f"torque on {v.design_slope_deg:g} deg / top speed at base rpm"))
    r.values.update(T_rated=T_rated, T_design=T_design)
