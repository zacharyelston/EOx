"""48 V bus: SELV, unit branches, main protection, precharge, and the
power/current/runtime of each operating mode."""

from __future__ import annotations

import math

from eox.calcs.common import (AMPACITY_105C, ENGINE_SPACE_DERATE_105C, OHM_PER_KM, Report, pack_voltages,
                              pick_awg, pick_step, tractive_force)
from eox.checks import Check


def unit_input_w(p, shaft_w: float) -> float:
    """Battery power a unit draws to deliver `shaft_w` at its shaft."""
    return shaft_w / (p.unit.motor_efficiency * p.unit.controller_efficiency)


def drivetrain_efficiency(p) -> float:
    return p.axle.efficiency * (0.97 if p.axle.extra_reduction > 1 else 1.0)


def steering_pump_w(p) -> float:
    """Average electrical draw of the hydraulic steering power unit while driving
    (zero for manual steering)."""
    s = p.steering
    if "hydraulic" not in s.type:
        return 0.0
    hyd = s.pump_flow_lpm / 60000 * s.relief_bar * 1e5
    return hyd / s.pump_efficiency * s.duty


def mode_power(p, tr, mode) -> dict[str, float]:
    """Average battery power (W) by consumer for an operating mode."""
    aux = p.aux.dcdc_output_w / p.aux.dcdc_efficiency + p.aux.quiescent_w
    out = {"drive": 0.0, "pto": 0.0, "hydraulic": 0.0, "steering": 0.0, "aux": aux, "units": 0}
    if mode.drive_speed_kmh > 0:
        fitted = ("deck",) if mode.pto_units else ()
        F = tractive_force(tr.mass(fitted=fitted), mode.drive_slope_deg, p.vehicle.rolling_resistance)
        wheel_w = F * mode.drive_speed_kmh / 3.6 * p.vehicle.duty_overhead
        out["drive"] = unit_input_w(p, wheel_w / drivetrain_efficiency(p))
        out["steering"] = steering_pump_w(p)
        out["units"] += tr.drive_units                      # one unit per drive-axle module
    if mode.pto_units:
        out["pto"] = unit_input_w(p, mode.pto_power_w)
        out["units"] += mode.pto_units
    if mode.hydraulic_units:
        out["hydraulic"] = unit_input_w(p, mode.hydraulic_power_w / p.bus.pump_efficiency)
        out["units"] += mode.hydraulic_units
    out["total"] = sum(v for k, v in out.items() if k != "units")
    return out


def run(p, tr, r: Report):
    b, u, bus, pr = p.battery, p.unit, p.bus, p.protection
    V_min, V_nom, V_max = pack_voltages(b)
    grp = "Bus"

    # ---- SELV -----------------------------------------------------------------
    r.add(
        Check(grp, "max pack voltage (full charge)", round(V_max, 1), "V", pr.selv_limit_v, "<=",
              note="SELV: <= 60 V DC (UL 2271 s14.2)"),
        Check(grp, "pack voltage at BMS over-voltage trip (single fault)", round(b.cells_series * b.bms_cell_ovp_v, 1),
              "V", pr.selv_limit_v, "<=", 0.02, note="charger fault must be stopped by the BMS below 3.75 V/cell"),
    )

    # ---- one unit branch ------------------------------------------------------
    I_unit = unit_input_w(p, u.rated_power_w) / V_min                 # rated, at an empty pack
    br_need = max(pr.fuse_continuous_factor * I_unit, u.controller_battery_limit_a)
    br_fuse = pick_step(pr.branch_fuse_steps_a, br_need)
    br_awg = pick_awg(br_fuse)
    br_drop = I_unit * OHM_PER_KM[br_awg] / 1000 * bus.branch_conductor_length_m / V_min * 100
    r.add(
        Check(grp, "unit current at rated power, empty pack", round(I_unit, 1), "A",
              note=f"{u.rated_power_w:.0f} W shaft / motor {u.motor_efficiency:g} / controller {u.controller_efficiency:g} / {V_min:.0f} V"),
        Check(grp, f"branch fuse >= max(1.25 x I_unit, controller limit)", br_fuse, "A", round(br_need, 1), ">=",
              note=f"{pr.branch_fuse_family}, {br_fuse:.0f} A, one per unit"),
        Check(grp, f"branch fuse <= branch cable ampacity ({br_awg} AWG, 105C)", br_fuse, "A",
              AMPACITY_105C[br_awg], "<=", note=">= 50 V circuits: fuse <= 100% ampacity (33 CFR 183.455)"),
        Check(grp, f"branch voltage drop, {bus.branch_conductor_length_m:g} m round trip", round(br_drop, 2), "%",
              pr.max_voltage_drop_pct, "<="),
        Check(grp, "branch fuse DC voltage rating", pr.branch_fuse_voltage_rating_v, "V", round(V_max, 1), ">=", 0.2,
              note="REF rating; confirm on the datasheet"),
    )

    # ---- whole bus --------------------------------------------------------------
    n = bus.max_simultaneous_units
    I_bus = n * I_unit
    I_peak = n * u.controller_battery_limit_a
    main_need = max(pr.fuse_continuous_factor * I_bus, I_peak)
    main_fuse = pick_step(pr.main_fuse_steps_a, main_need)
    derate = ENGINE_SPACE_DERATE_105C if pr.conductor_in_engine_space else 1.0
    main_awg = pick_awg(main_fuse, derate)
    R_main_cable = OHM_PER_KM[main_awg] / 1000 * pr.main_conductor_length_m
    I_sc = V_max / (b.internal_resistance_mohm / 1000 + R_main_cable)
    main_drop = I_bus * R_main_cable / V_min * 100
    r.add(
        Check(grp, f"bus continuous: {n} units at rated vs pack rating", round(I_bus), "A", b.max_continuous_a, "<=", 0.1),
        Check(grp, f"bus peak: {n} controllers at their limit vs pack peak", I_peak, "A", b.max_peak_a, "<="),
        Check(grp, f"main fuse ({pr.main_fuse_family}) >= max(1.25 x bus, bus peak)", main_fuse, "A",
              round(main_need), ">=", note=f"selected {main_fuse:.0f} A"),
        Check(grp, f"main fuse <= main cable ampacity ({main_awg} AWG, 105C)", main_fuse, "A",
              round(AMPACITY_105C[main_awg] * derate), "<="),
        Check(grp, "main cable voltage drop", round(main_drop, 2), "%", pr.max_voltage_drop_pct, "<="),
        Check(grp, "main fuse DC voltage rating", pr.main_fuse_voltage_rating_v, "V", round(V_max, 1), ">="),
        Check(grp, "main fuse interrupt rating vs pack short circuit", pr.main_fuse_interrupt_rating_a, "A",
              round(I_sc), ">=", note=f"I_sc ~ V_max / (R_pack + R_cable) = {I_sc:,.0f} A"),
        Check(grp, "branch fuse interrupt rating vs pack short circuit", pr.branch_fuse_interrupt_rating_a, "A",
              round(I_sc), ">=", note="REF rating; confirm on the datasheet"),
        Check(grp, "contactor continuous rating vs 1.25 x bus", pr.contactor_continuous_a, "A",
              round(pr.fuse_continuous_factor * I_bus), ">="),
        Check(grp, "contactor voltage rating vs max pack voltage", pr.contactor_voltage_rating_v, "V", round(V_max, 1), ">="),
    )

    # ---- precharge: every unit's controller capacitance sits on the bus ---------
    C = bus.units_installed * u.controller_capacitance_uf * 1e-6
    tau = pr.precharge_resistor_ohm * C
    r.add(
        Check(grp, f"precharge to 95% ({bus.units_installed} controllers on the bus)", round(-tau * math.log(0.05), 2), "s",
              pr.precharge_max_time_s, "<="),
        Check(grp, "precharge resistor if left on into a short", round(V_max ** 2 / pr.precharge_resistor_ohm), "W",
              pr.precharge_resistor_w, "<=", note="needs a timed precharge so a downstream short can't cook it"),
    )

    # ---- operating modes ----------------------------------------------------------
    E_use = V_nom * b.capacity_ah * b.usable_dod
    for name, mode in vars(p.modes).items():
        pw = mode_power(p, tr, mode)
        I_avg = pw["total"] / V_nom
        parts = ", ".join(f"{k} {v:.0f}" for k, v in pw.items() if k not in ("total", "units") and v)
        g = f"Mode {name}"
        r.add(
            Check(g, "units running", pw["units"], "", n, "<=", note=f"bus is sized for {n}"),
            Check(g, "average battery power", round(pw["total"]), "W", note=parts + " W"),
            Check(g, "average battery current", round(I_avg, 1), "A", b.max_continuous_a, "<="),
            Check(g, "runtime on one charge", round(E_use / pw["total"], 2), "h", mode.runtime_min_h, ">=",
                  warn_limit=mode.runtime_target_h, note=f"{E_use:,.0f} Wh usable"),
        )
        r.values[f"mode_{name}_A"] = I_avg
        r.values[f"mode_{name}_runtime_h"] = E_use / pw["total"]
    r.values.update(I_unit=I_unit, I_bus=I_bus, V_nom=V_nom, main_fuse=main_fuse, branch_fuse=br_fuse,
                    main_awg=main_awg, branch_awg=br_awg)
