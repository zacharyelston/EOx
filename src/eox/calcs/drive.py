"""Drive: golf-cart axle modules, one 3 HP unit each.

Per-motor torque = (tractive force / driven axles) x tire radius / (ratio x
efficiency). Torque at or under the unit's rated torque is continuous duty;
up to its peak is short-time duty (motor heats); past the peak it can't climb.
"""

from __future__ import annotations

import math

from eox.calcs.bus import drivetrain_efficiency
from eox.calcs.common import Report, tractive_force
from eox.checks import Check
from eox.tractor import DECK


def _per_motor(p, tr, slope_deg: float, extra: float | None = None, ratio: float | None = None,
               fitted: tuple = DECK) -> float:
    """Torque per drive motor. `ratio` overrides the overall ratio outright
    (a different rear end); `extra` multiplies the stock ratio (a chain stage).
    Climbs are checked with the deck fitted: mowing a slope is the design case."""
    a = p.axle
    extra = a.extra_reduction if extra is None else extra
    overall = ratio if ratio is not None else a.ratio * extra
    eta = a.efficiency * (0.97 if overall > a.ratio * 1.5 else 1.0)       # chain stage loss
    F = tractive_force(tr.mass(fitted=fitted), slope_deg, p.vehicle.rolling_resistance)
    return F / tr.drive_units * (a.tire_diameter / 2000) / (overall * eta)


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
    label = next((o.label for o in a.gearing_options if abs(o.ratio - ratio) < 0.05), None)
    r.add(
        Check(grp, "overall ratio (rear end x extra stage)", round(ratio, 1), ":1",
              note=label or f"{a.ratio:g}:1 rear end, {a.extra_reduction:g}:1 stage added"),
        Check(grp, f"motor torque each, {v.design_slope_deg:g} deg climb, deck fitted (sustained)", round(T_design, 1), "N*m",
              round(T_peak, 1), "<=", warn_limit=round(T_rated, 1),
              note=f"{T_design / T_rated:.1f}x rated: over rated = short-time duty, motor heats"),
        Check(grp, f"motor torque each, {v.max_slope_deg:g} deg climb, deck fitted (short)", round(T_max, 1), "N*m",
              round(T_peak, 1), "<=", 0.1, note=f"{T_max / T_rated:.1f}x rated"),
        Check(grp, f"motor speed at {v.top_speed_kmh:g} km/h", round(n_top), "rpm", u.max_speed_rpm, "<=", 0.05),
        Check(grp, "motor speed at mowing pace vs base speed", round(n_mow / u.base_speed_rpm * 100), "%",
              note="self-cooling fan works poorly this slow; watch motor temperature"),
        Check(grp, f"drive power available per unit at {v.top_speed_kmh:g} km/h", round(T_rated * n_top * 2 * math.pi / 60),
              "W", note=f"rated torque x speed, of {u.rated_power_w:.0f} W: the rest of the unit is geared away"),
    )

    # traction vs motor peak: which one limits a hard pull
    driven = [ax.name for ax in tr.axles if ax.driven]

    def grip(slope):
        loads = tr.axle_loads_n(slope, fitted=DECK)
        return v.traction_coefficient * sum(loads[n] for n in driven)

    F_motors = tr.drive_units * T_peak * a.ratio * a.extra_reduction * drivetrain_efficiency(p) / (a.tire_diameter / 2000)
    lo_, hi_ = 0.0, 45.0
    for _ in range(50):                                   # steepest climb the driven tyres can grip
        mid = (lo_ + hi_) / 2
        if grip(mid) >= tractive_force(tr.mass(fitted=DECK), mid, v.rolling_resistance):
            lo_ = mid
        else:
            hi_ = mid
    layout = "AWD" if tr.drive_units == len(tr.axles) else "rear-drive"
    r.add(
        Check(grp, "peak tractive force on the flat: motors / tyre grip", f"{F_motors:,.0f} / {grip(0):,.0f}", "N",
              note="grip limits first (wheels slip before motors stall)" if grip(0) < F_motors else "motors limit first"),
        Check(grp, f"steepest climb on grip ({layout})", round(lo_, 1), "deg", v.max_slope_deg, ">=", 0.1,
              note=f"turf traction {v.traction_coefficient:g}; climbing shifts load onto the rear axle"),
    )

    # gearing options (issue 2): OEM rear ends and added chain stages
    for opt in a.gearing_options:
        t10 = _per_motor(p, tr, v.design_slope_deg, ratio=opt.ratio)
        t15 = _per_motor(p, tr, v.max_slope_deg, ratio=opt.ratio)
        top = u.base_speed_rpm / opt.ratio * math.pi * a.tire_diameter / 1000 * 60 / 1000
        r.add(Check(grp, f"gearing option: {opt.label} ({opt.ratio:g}:1)",
                    f"{t10 / T_rated:.1f}x / {t15 / T_rated:.1f}x rated, {top:.0f} km/h", "",
                    note=f"torque on {v.design_slope_deg:g} / {v.max_slope_deg:g} deg; top speed at base rpm"))
    r.values.update(T_rated=T_rated, T_design=T_design)
