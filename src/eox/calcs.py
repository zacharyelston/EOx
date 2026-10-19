"""Power box engineering checks.

Screening-level hand calcs: each one states its model in the docstring, uses
parameters from design/powerbox.toml, and returns Check rows. They are meant
to catch bad numbers early, not to replace testing or a stamped analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from eox.checks import Check
from eox.powerbox import Layout, _rod_y

G0 = 9.81
SIGMA = 5.670e-8

# 33 CFR 183.425 Table 5 (same basis as ABYC E-11), 105 C insulation, outside
# engine spaces. https://www.law.cornell.edu/cfr/text/33/183.425
AMPACITY_105C = {"10": 60, "8": 80, "6": 120, "4": 160, "2": 210, "1/0": 285, "2/0": 330}
ENGINE_SPACE_DERATE_105C = 0.85
# annealed copper, ohm per km at 20 C
OHM_PER_KM = {"10": 3.277, "8": 2.061, "6": 1.296, "4": 0.8152, "2": 0.5127, "1/0": 0.3224, "2/0": 0.2557}

# Roark, simply supported rectangular plate, uniform load, nu = 0.3:
# sigma_max = beta * q * b^2 / t^2 ; y_max = alpha * q * b^4 / (E t^3), b = short side
_ROARK_RATIO = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0, 4.0, 5.0, 1e9]
_ROARK_BETA = [0.2874, 0.3762, 0.4530, 0.5172, 0.5688, 0.6102, 0.7134, 0.7410, 0.7476, 0.7500]
_ROARK_ALPHA = [0.0444, 0.0616, 0.0770, 0.0906, 0.1017, 0.1110, 0.1335, 0.1400, 0.1417, 0.1421]


def _interp(x, xs, ys):
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            f = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + f * (ys[i + 1] - ys[i])
    return ys[-1]


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    values: dict[str, float] = field(default_factory=dict)

    def add(self, *cs: Check):
        self.checks.extend(cs)

    def worst(self) -> str:
        order = ["FAIL", "WARN", "PASS", "INFO"]
        return min((c.status for c in self.checks), key=order.index, default="INFO")


def run(p, lay: Layout) -> Report:
    r = Report()
    layout_checks(p, lay, r)
    for part in lay.parts:
        r.add(*part.scs_checks(p.scs))
    drive(p, r)
    energy(p, r)
    electrical(p, r)
    thermal(p, lay, r)
    structural(p, lay, r)
    mass_cg(p, lay, r)
    return r


# ---------------------------------------------------------------------------
def layout_checks(p, lay: Layout, r: Report):
    """Components inside the shells and clear of each other."""
    grp = "Layout"
    t = lay.t
    inner = (-lay.L_in / 2, lay.L_in / 2, -lay.W_in / 2, lay.W_in / 2, t, lay.z_top - t)
    for b in lay.bodies:
        x0, x1, y0, y1, z0, z1 = b.bounds()
        margin = min(x0 - inner[0], inner[1] - x1, y0 - inner[2], inner[3] - y1, z0 - inner[4], inner[5] - z1)
        r.add(Check(grp, f"{b.name} inside shell", round(margin, 1), "mm", -0.01, ">="))
    bat = lay.body("battery")
    head = (lay.z_top - t) - bat.bounds()[5]
    r.add(Check(grp, "headroom over battery for terminals", round(head, 1), "mm",
                p.battery.terminal_clearance, ">="))
    names = [b.name for b in lay.bodies]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = lay.bodies[i].bounds(), lay.bodies[j].bounds()
            gap = max(b[0] - a[1], a[0] - b[1], b[2] - a[3], a[2] - b[3], b[4] - a[5], a[4] - b[5])
            r.add(Check(grp, f"{names[i]} / {names[j]} clearance", round(gap, 1), "mm", 0.0, ">="))
    ctl = lay.body("controller")
    r.add(Check(grp, "controller mounts below tray rim", round(ctl.bounds()[5], 1), "mm",
                lay.tray_h - 10, "<=", note="its rivnuts go in the tray wall"))
    r.values.update(L_out=lay.L_out, W_out=lay.W_out, H_out=lay.H_out)


# ---------------------------------------------------------------------------
def _vehicle(p):
    v = p.vehicle
    m = v.mass_tractor_kg + v.mass_operator_kg + v.mass_payload_kg
    return v, m, v.tire_diameter / 2000


def drive(p, r: Report):
    """Tractive force F = m g (sin th + Crr cos th); wheel torque = F r;
    motor torque = wheel torque / (G eta). Rated torque = P / omega."""
    grp = "Drive"
    v, m, rw = _vehicle(p)
    mot = p.motor
    G, eta = v.reduction_ratio, v.drivetrain_efficiency
    th = math.radians(v.design_grade_deg)
    F_grade = m * G0 * (math.sin(th) + v.rolling_resistance * math.cos(th))
    T_motor_grade = F_grade * rw / (G * eta)
    T_rated = mot.rated_power_w / (2 * math.pi * mot.rated_speed_rpm / 60)
    n_motor_top = v.top_speed_kmh / 3.6 / (2 * math.pi * rw) * 60 * G
    P_grade = F_grade * v.grade_speed_kmh / 3.6 / eta
    F_peak = mot.peak_torque_nm * G * eta / rw

    # steepest grade at rated (continuous) torque
    F_rated = T_rated * G * eta / rw
    lo, hi = 0.0, math.pi / 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if m * G0 * (math.sin(mid) + v.rolling_resistance * math.cos(mid)) < F_rated:
            lo = mid
        else:
            hi = mid
    r.add(
        Check(grp, f"motor speed at {v.top_speed_kmh:g} km/h", round(n_motor_top), "rpm", mot.max_speed_rpm, "<=", 0.05),
        Check(grp, f"motor torque to climb {v.design_grade_deg:g} deg (continuous)", round(T_motor_grade, 2), "N*m",
              round(T_rated, 2), "<=", 0.10, note=f"rated torque = {T_rated:.2f} N*m"),
        Check(grp, f"motor power to climb at {v.grade_speed_kmh:g} km/h", round(P_grade), "W", mot.rated_power_w, "<=", 0.10),
        Check(grp, "grade start: peak force / grade force", round(F_peak / F_grade, 2), "x", 1.3, ">=",
              note="room to accelerate from standstill on the design slope"),
        Check(grp, "steepest grade at rated torque", round(math.degrees(lo), 1), "deg",
              note="INFO; slope limits for the operator are a tractor-level decision"),
    )
    r.values.update(F_grade=F_grade, T_rated=T_rated)


def energy(p, r: Report):
    """Average battery power = flat-cruise wheel power x overhead / drive
    efficiency chain, plus DC-DC and quiescent loads."""
    grp = "Energy"
    v, m, _ = _vehicle(p)
    b, mot, ctl, aux = p.battery, p.motor, p.controller, p.aux
    P_wheel = v.rolling_resistance * m * G0 * v.cruise_speed_kmh / 3.6 * v.duty_overhead
    P_drive = P_wheel / (v.drivetrain_efficiency * mot.efficiency * ctl.efficiency)
    P_aux = aux.dcdc_output_w / aux.dcdc_efficiency + aux.quiescent_w + p.vent.fan_power_w
    P_batt = P_drive + P_aux
    V_nom = b.cells_series * b.cell_nominal_v
    E_rated = V_nom * b.capacity_ah
    E_use = E_rated * b.usable_dod
    hours = E_use / P_batt
    r.add(
        Check(grp, "pack energy (rated)", round(E_rated), "Wh"),
        Check(grp, "average battery power, mowing pace", round(P_batt), "W", note=f"drive {P_drive:.0f} W + aux {P_aux:.0f} W"),
        Check(grp, "runtime, drive only", round(hours, 2), "h", v.runtime_target_h, ">=", 0.15,
              note="mower deck load not included yet"),
    )
    r.values.update(P_batt_avg=P_batt, P_shaft_avg=P_wheel / v.drivetrain_efficiency, V_nom=V_nom)


def electrical(p, r: Report):
    """SELV ceiling, current budget, fuse/conductor coordination (33 CFR 183),
    voltage drop, short-circuit current vs fuse AIC, precharge RC."""
    grp = "Electrical"
    b, mot, ctl, pr = p.battery, p.motor, p.controller, p.protection
    V_max = b.cells_series * b.cell_max_v
    V_fault = b.cells_series * b.bms_cell_ovp_v
    V_min = b.cells_series * b.cell_min_v
    I_cont = mot.rated_power_w / (mot.efficiency * ctl.efficiency) / V_min
    I_peak = ctl.battery_current_limit_a

    r.add(
        Check(grp, "max pack voltage (full charge)", round(V_max, 1), "V", pr.selv_limit_v, "<=",
              note="SELV: <= 60 V DC (UL 2271 s14.2)"),
        Check(grp, "pack voltage at BMS over-voltage trip (single fault)", round(V_fault, 1), "V",
              pr.selv_limit_v, "<=", 0.02, note="charger fault must be stopped by the BMS below 3.75 V/cell"),
        Check(grp, "continuous current (rated power at empty pack)", round(I_cont, 1), "A",
              b.max_continuous_a, "<=", 0.15),
        Check(grp, "controller battery limit vs pack peak", I_peak, "A", b.max_peak_a, "<="),
    )

    need = max(pr.fuse_continuous_factor * I_cont, I_peak)
    fuse = next((f for f in pr.fuse_steps_a if f >= need), pr.fuse_steps_a[-1])
    derate = ENGINE_SPACE_DERATE_105C if pr.conductor_in_engine_space else 1.0
    awg = next(a for a, amp in AMPACITY_105C.items() if amp * derate >= fuse)
    ampacity = AMPACITY_105C[awg] * derate
    R_wire = OHM_PER_KM[awg] / 1000 * pr.main_conductor_length_m
    drop_pct = I_cont * R_wire / V_min * 100
    I_sc = V_max / (b.internal_resistance_mohm / 1000 + R_wire)
    r.add(
        Check(grp, f"main fuse ({pr.fuse_family}) >= max(1.25 x I_cont, I_peak)", fuse, "A", round(need, 1), ">=",
              note=f"selected {fuse} A"),
        Check(grp, f"fuse <= conductor ampacity ({awg} AWG, 105C{', engine-space' if derate < 1 else ''})", fuse, "A",
              round(ampacity), "<=", note=">= 50 V circuits: fuse <= 100% ampacity (33 CFR 183.455)"),
        Check(grp, "main conductor voltage drop", round(drop_pct, 2), "%", pr.max_voltage_drop_pct, "<="),
        Check(grp, "fuse DC voltage rating vs max pack voltage", pr.fuse_voltage_rating_v, "V", round(V_max, 1), ">="),
        Check(grp, "fuse interrupt rating vs pack short-circuit current", pr.fuse_interrupt_rating_a, "A",
              round(I_sc), ">=", note=f"I_sc ~ V_max / (R_pack + R_wire) = {I_sc:,.0f} A"),
        Check(grp, "contactor continuous rating vs fuse", pr.contactor_continuous_a, "A", fuse, ">="),
        Check(grp, "contactor voltage rating vs max pack voltage", pr.contactor_voltage_rating_v, "V", round(V_max, 1), ">="),
    )

    C = ctl.input_capacitance_uf * 1e-6
    tau = pr.precharge_resistor_ohm * C
    t95 = -tau * math.log(0.05)
    r.add(
        Check(grp, "precharge time to 95%", round(t95, 2), "s", pr.precharge_max_time_s, "<="),
        Check(grp, "precharge inrush", round(V_max / pr.precharge_resistor_ohm, 2), "A"),
        Check(grp, "precharge resistor if left on into a short", round(V_max ** 2 / pr.precharge_resistor_ohm), "W",
              pr.precharge_resistor_w, "<=",
              note="needs a timed precharge or PTC so a downstream short can't cook it"),
    )
    r.values.update(I_cont=I_cont, I_peak=I_peak, fuse=fuse, awg=awg, V_min=V_min, V_max=V_max)


def thermal(p, lay: Layout, r: Report):
    """Two-zone steady-state network: sealed battery bay (B) and ventilated
    motor bay (M), split by the bulkhead. Pack temperature ~ B air.

    Nodes: B air, B shell, M air, M shell.
      air <-> own shell     h_in x inner area
      shell -> ambient      (h_out + h_rad) x outer area; solar on each zone's share of the lid
      B air <-> M air       through the bulkhead plate (h_in on both faces)
      B shell <-> M shell   conduction along the aluminium shell
      M air -> ambient      vent flow rho*cp*Vdot: the fan, or stack effect if the fan is off
    The motor flange and controller baseplate conduct their share straight into the M shell.
    """
    grp = "Thermal"
    th, fin, b, mot, ctl, aux, vn = p.thermal, p.finish, p.battery, p.motor, p.controller, p.aux, p.vent
    P_shaft = r.values["P_shaft_avg"]
    q_motor = P_shaft * (1 / mot.efficiency - 1)
    q_ctl = P_shaft / mot.efficiency * (1 / ctl.efficiency - 1)
    I_avg = r.values["P_batt_avg"] / r.values["V_nom"]
    R_pack = b.internal_resistance_mohm / 1000
    q_dcdc = aux.dcdc_output_w * (1 / aux.dcdc_efficiency - 1)
    q_bms = aux.quiescent_battery_bay_w
    mowing = {
        "ab": I_avg ** 2 * R_pack + q_bms,
        "am": ((1 - mot.heat_to_wall_fraction) * q_motor + (1 - ctl.heat_to_wall_fraction) * q_ctl
               + q_dcdc + aux.quiescent_w - q_bms + vn.fan_power_w),
        "wm": mot.heat_to_wall_fraction * q_motor + ctl.heat_to_wall_fraction * q_ctl,
    }
    charging = {"ab": th.charge_current_a ** 2 * R_pack + q_bms, "am": 0.0, "wm": 0.0}

    # geometry, metres
    cover = lay.part("PB-102")
    Lc, Wc, H = cover.A / 1000, cover.B / 1000, lay.H_out / 1000
    Li, Wi, Hi = lay.L_in / 1000, lay.W_in / 1000, lay.H_in / 1000
    xb = (lay.x.bh_x + lay.t / 2) / 1000
    Lb, Lm = xb + Lc / 2, Lc / 2 - xb
    A_out_b, A_out_m = Lb * (2 * Wc + 2 * H) + Wc * H, Lm * (2 * Wc + 2 * H) + Wc * H
    hb = th.h_inside_w_m2k * ((xb + Li / 2) * (2 * Wi + 2 * Hi) + Wi * Hi)
    hm = th.h_inside_w_m2k * ((Li / 2 - xb) * (2 * Wi + 2 * Hi) + Wi * Hi)
    G_bh = Wi * Hi * th.h_inside_w_m2k / 2
    G_sh = p.gauge.k_w_mk * (lay.t / 1000) * 2 * (Wc + H) / ((Lb + Lm) / 2)
    sun = fin.alpha * th.solar_w_m2 * Wc
    sun_b, sun_m = sun * Lb, sun * Lm

    slots = [h for h in lay.part("PB-101").holes if h.label == "inlet slot"]
    A_in = sum(h.area for h in slots) / 1e6
    A_out = math.pi / 4 * (vn.fan_opening / 1000) ** 2
    A_eff = A_in * A_out / math.hypot(A_in, A_out)
    H_stack = lay.x.fan_z / 1000
    T_amb_K = th.ambient_c + 273.15
    rho_cp = 1.15 * 1007

    def solve(q, fan_on):
        x = np.full(4, 10.0)                       # excess over ambient: B air, B shell, M air, M shell
        for _ in range(200):
            h_rad = lambda dT: 4 * fin.eps * SIGMA * (th.ambient_c + dT / 2 + 273.15) ** 3
            Ho_b = (th.h_outside_w_m2k + h_rad(x[1])) * A_out_b
            Ho_m = (th.h_outside_w_m2k + h_rad(x[3])) * A_out_m
            v_stack = vn.discharge_coefficient * A_eff * math.sqrt(2 * G0 * H_stack * max(x[2], 0) / T_amb_K)
            vdot = max(v_stack, vn.fan_flow_m3h / 3600 if fan_on else 0.0)
            Gv = rho_cp * vdot
            M = np.array([[hb + G_bh, -hb, -G_bh, 0],
                          [-hb, hb + Ho_b + G_sh, 0, -G_sh],
                          [-G_bh, 0, G_bh + hm + Gv, -hm],
                          [0, -G_sh, -hm, hm + Ho_m + G_sh]])
            new = np.linalg.solve(M, [q["ab"], sun_b, q["am"], q["wm"] + sun_m])
            if np.max(np.abs(new - x)) < 1e-4:
                break
            x = 0.5 * x + 0.5 * new
        return th.ambient_c + x, vdot * 3600

    T_fan, v_fan = solve(mowing, True)
    T_dead, v_dead = solve(mowing, False)
    T_chg, _ = solve(charging, False)
    w_run = th.battery_margin_c / b.max_temp_discharge_c
    w_chg = th.battery_margin_c / b.max_temp_charge_c
    w_ctl = th.battery_margin_c / ctl.max_ambient_c
    sun_note = f"{th.ambient_c:g} C, {th.solar_w_m2:g} W/m2 sun, still air"
    r.add(
        Check(grp, "heat in motor bay at mowing pace", round(mowing["am"] + mowing["wm"]), "W",
              note=f"motor {q_motor:.0f}, controller {q_ctl:.0f}, DC-DC {q_dcdc:.0f}, idle+fan "
                   f"{aux.quiescent_w - q_bms + vn.fan_power_w:g}"),
        Check(grp, "heat in battery bay at mowing pace", round(mowing["ab"], 1), "W", note="pack I^2R + BMS"),
        Check(grp, f"solar load on lid ({p.enclosure.finish})", round(sun_b + sun_m), "W"),
        Check(grp, "motor bay vent flow: fan / fan failed (stack)", f"{v_fan:.0f} / {v_dead:.0f}", "m3/h",
              note=f"inlet {A_in * 1e4:.0f} cm2 floor slots, outlet {A_out * 1e4:.0f} cm2 fan opening"),
        Check(grp, "pack temp, mowing, fan running", round(T_fan[0], 1), "C", b.max_temp_discharge_c, "<=", w_run,
              note=sun_note),
        Check(grp, "pack temp, mowing, fan failed", round(T_dead[0], 1), "C", b.max_temp_discharge_c, "<=", w_run,
              note="a dead fan must not take the pack over its rating"),
        Check(grp, "motor bay air, fan running", round(T_fan[2], 1), "C", ctl.max_ambient_c, "<=", w_ctl,
              note="controller full-power ambient (REF)"),
        Check(grp, "motor bay air, fan failed", round(T_dead[2], 1), "C",
              note="above the controller rating it derates itself: less power, not a hazard"),
        Check(grp, "pack temp, parked in sun while charging", round(T_chg[0], 1), "C", b.max_temp_charge_c, "<=", w_chg,
              note=f"{th.charge_current_a:g} A charge, fan off"),
    )


def _u_channel_Z(web: float, flange: float, t: float) -> float:
    """Section modulus (mm^3) of a U-channel, web horizontal, flanges up,
    bending about the horizontal axis. Square-corner approximation."""
    A_w, y_w = web * t, t / 2
    A_f, y_f = (flange - t) * t, t + (flange - t) / 2
    A = A_w + 2 * A_f
    yb = (A_w * y_w + 2 * A_f * y_f) / A
    I = (web * t ** 3 / 12 + A_w * (yb - y_w) ** 2
         + 2 * (t * (flange - t) ** 3 / 12 + A_f * (y_f - yb) ** 2))
    return I / max(yb, flange - yb)


def structural(p, lay: Layout, r: Report):
    grp = "Structural"
    g, ld, b = p.gauge, p.loads, p.battery
    allow = g.yield_mpa / ld.safety_factor
    allow_crash = g.yield_mpa / ld.crash_safety_factor
    W_bat = b.mass_kg * G0
    t = g.t

    # Floor under the pack: simply supported plate between the walls, pack
    # weight x vertical g spread over the floor under it (worst case: box only
    # supported at its edges).
    a, bb = lay.x.bh_x + lay.L_in / 2, lay.W_in          # battery bay: -x wall to bulkhead
    a, bb = max(a, bb), min(a, bb)
    q = W_bat * ld.vertical_g / (a * bb)                    # N/mm^2
    beta = _interp(a / bb, _ROARK_RATIO, _ROARK_BETA)
    alpha = _interp(a / bb, _ROARK_RATIO, _ROARK_ALPHA)
    sig = beta * q * bb ** 2 / t ** 2
    defl = alpha * q * bb ** 4 / (g.E_mpa * t ** 3)
    r.add(Check(grp, f"floor bending under pack at {ld.vertical_g:g} g", round(sig, 1), "MPa", round(allow, 1), "<=", 0.1,
                note="if supported only at its edges; frame rails under the floor make this much lower"),
          Check(grp, "floor deflection, same case", round(defl, 2), "mm", round(3 * t, 1), "<=",
                note="small-deflection theory; above ~t it over-predicts"))

    # Clamp bars: net uplift (vertical_g - 1) shared by the bars, load spread
    # over the pack width on a span between the two rods.
    c = p.battery_clamp
    span = 2 * _rod_y(p, lay)
    F_bar = W_bat * (ld.vertical_g - 1) / c.count
    M = F_bar / 4 * (span - b.width / 2)
    Z = _u_channel_Z(c.web, c.flange, t)
    rod_load = c.rod_preload_n + F_bar / 2
    friction = c.pad_friction * (4 * c.rod_preload_n + W_bat) if c.count >= 2 else 0
    r.add(
        Check(grp, "clamp bar bending (uplift)", round(M / Z, 1), "MPa", round(allow, 1), "<=", 0.1),
        Check(grp, "clamp rod rivnut load (preload + uplift)", round(rod_load), "N",
              round(c.rivnut_pullout_n / ld.safety_factor), "<=", 0.1, note="rivnut pull-out is REF; verify"),
        Check(grp, f"lateral hold by clamp friction at {ld.lateral_g:g} g", round(friction), "N",
              round(W_bat * ld.lateral_g), ">=", 0.1),
    )

    # Battery stops: strike an obstacle at top speed, decel = v^2 / (2 d).
    v = p.vehicle.top_speed_kmh / 3.6
    n_crash = v ** 2 / (2 * ld.crash_stop_distance / 1000) / G0
    s = p.battery_stop
    F = W_bat * n_crash
    M_stop = F * s.height / 2                                    # N*mm, load at mid-height
    Z_stop = s.length * t ** 2 / 6
    r.add(
        Check(grp, f"crash decel (top speed into obstacle, {ld.crash_stop_distance:g} mm crush)", round(n_crash, 1), "g",
              note="garden-tractor estimate; road-vehicle ECE R100 pulses are 10-28 g"),
        Check(grp, "battery stop upright bending (crash)", round(M_stop / Z_stop, 1), "MPa", round(allow_crash, 1), "<=", 0.1),
        Check(grp, "battery stop rivet shear (crash)", round(F / s.rivets), "N", s.rivet_shear_n, "<=", 0.2,
              note="rivet shear rating is REF; verify"),
    )

    # Motor mount: bolt group carries torque reaction + chain pull + motor
    # weight; bearing on wall + doubler.
    m = p.motor
    r_spr = ld.chain_pitch / (2 * math.sin(math.pi / ld.sprocket_teeth))
    F_chain = m.peak_torque_nm * 1000 / r_spr
    W_m = m.mass_kg * G0 * ld.vertical_g
    F_bolt = (m.peak_torque_nm * 1000 / (m.bolt_count * m.bolt_pcd / 2)
              + math.hypot(F_chain, W_m) / m.bolt_count)
    A_s = 0.7854 * (m.bolt_diameter - 0.9382 * 1.25) ** 2          # M8 stress area ~36.6 mm^2
    bearing = F_bolt / (m.bolt_diameter * (t + p.doubler_gauge.t))
    # overhung chain pull and motor weight bend the wall: bolt tension by couple
    M_wall = F_chain * ld.chain_offset_from_wall + W_m * m.length / 2
    arm = m.bolt_pcd * math.sin(math.radians(45)) * (m.bolt_count / 2)
    r.add(
        Check(grp, f"chain pull at peak torque (#40, {ld.sprocket_teeth}T)", round(F_chain), "N"),
        Check(grp, "motor bolt shear stress", round(F_bolt / A_s, 1), "MPa", ld.bolt_shear_allow_mpa, "<=", 0.1),
        Check(grp, "bearing on wall + doubler at motor bolts", round(bearing, 1), "MPa",
              round(ld.bearing_yield_factor * g.yield_mpa / ld.safety_factor, 1), "<=", 0.1),
        Check(grp, "motor bolt tension from overhung loads", round(M_wall / arm), "N",
              round(A_s * 600 / ld.safety_factor), "<=", note="class 8.8 proof 600 MPa"),
    )


def mass_cg(p, lay: Layout, r: Report):
    """Mass of fabricated parts + components; CG in the box frame."""
    grp = "Mass"
    m_tot, mx, my, mz = 0.0, 0.0, 0.0, 0.0
    for b in lay.bodies:
        m_tot += b.mass
        mx, my, mz = mx + b.mass * b.center[0], my + b.mass * b.center[1], mz + b.mass * b.center[2]
    sheet = 0.0
    for pl in lay.placed:
        mp = pl.part.mass_kg()
        sheet += mp
        bb = pl.solid().bounding_box().center()
        m_tot += mp
        mx, my, mz = mx + mp * bb.X, my + mp * bb.Y, mz + mp * bb.Z
    r.add(
        Check(grp, "sheet metal parts", round(sheet, 2), "kg"),
        Check(grp, "power box (excl. wiring/hardware)", round(m_tot, 1), "kg"),
        Check(grp, "CG x / y / z in box frame", f"{mx / m_tot:.0f} / {my / m_tot:.0f} / {mz / m_tot:.0f}", "mm",
              note="origin: centre of tray floor underside; feeds the tractor stability calc"),
    )
    r.values.update(mass=m_tot, sheet_mass=sheet)
