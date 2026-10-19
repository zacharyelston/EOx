"""Battery & distribution box: fit, SendCutSend rules, thermal, structure.

Screening-level hand calcs: each one states its model in the docstring, uses
parameters from the design files, and returns Check rows. They are meant to
catch bad numbers early, not to replace testing or a stamped analysis.
"""

from __future__ import annotations

import math

from eox.calcs.common import (G0, ROARK_ALPHA, ROARK_BETA, ROARK_RATIO, SIGMA, Report, interp,
                              u_channel_Z)
from eox.checks import Check
from eox.powerbox import Layout, _rod_y


def run(p, lay: Layout, r: Report):
    layout_checks(p, lay, r)
    for part in lay.parts:
        r.add(*part.scs_checks(p.scs))
    thermal(p, lay, r)
    structural(p, lay, r)
    mass_cg(p, lay, r)


def layout_checks(p, lay: Layout, r: Report):
    """Components inside the shells and clear of each other."""
    grp = "Box layout"
    t = lay.t
    inner = (-lay.L_in / 2, lay.L_in / 2, -lay.W_in / 2, lay.W_in / 2, t, lay.z_top - t)
    for b in lay.bodies:
        x0, x1, y0, y1, z0, z1 = b.bounds()
        margin = min(x0 - inner[0], inner[1] - x1, y0 - inner[2], inner[3] - y1, z0 - inner[4], inner[5] - z1)
        r.add(Check(grp, f"{b.name} inside shell", round(margin, 1), "mm", -0.01, ">="))
    bat = lay.body("battery")
    r.add(Check(grp, "headroom over battery for terminals", round((lay.z_top - t) - bat.bounds()[5], 1), "mm",
                p.battery.terminal_clearance, ">="))
    for i, a in enumerate(lay.bodies):
        for b in lay.bodies[i + 1:]:
            A, B = a.bounds(), b.bounds()
            gap = max(B[0] - A[1], A[0] - B[1], B[2] - A[3], A[2] - B[3], B[4] - A[5], A[4] - B[5])
            r.add(Check(grp, f"{a.name} / {b.name} clearance", round(gap, 1), "mm", 0.0, ">="))
    L, W, H = lay.outer
    r.add(Check(grp, "outer size L x W x H (cover on)", f"{L:.0f} x {W:.0f} x {H:.0f}", "mm"))


def thermal(p, lay: Layout, r: Report):
    """Sealed box, steady state. Heat: pack I^2R at the mowing-mode current,
    I^2R in the contactor/fuse/bus bars, DC-DC loss, idle. Outside: (natural
    convection + radiation) x outer area carries that + solar on the lid.
    Inside: still air between the walls and the pack. Pack temp ~ inside air."""
    grp = "Box thermal"
    th, fin, b, aux, pr = p.thermal, p.finish, p.battery, p.aux, p.protection
    I = r.values["mode_mowing_A"]
    q_pack = I ** 2 * b.internal_resistance_mohm / 1000
    q_dist = I ** 2 * pr.distribution_resistance_mohm / 1000
    q_dcdc = aux.dcdc_output_w * (1 / aux.dcdc_efficiency - 1)
    q_int = q_pack + q_dist + q_dcdc + aux.quiescent_w
    L, W, H = (v / 1000 for v in lay.outer)
    A_out = 2 * (L * W + L * H + W * H)
    A_in = 2 * (lay.L_in * lay.W_in + lay.L_in * lay.H_in + lay.W_in * lay.H_in) / 1e6
    q_sun = fin.alpha * th.solar_w_m2 * L * W

    def steady(q_internal, q_solar):
        """Steady-state pack temp and the pack-to-ambient conductance (W/K)."""
        T = th.ambient_c + 10
        for _ in range(30):
            h_rad = 4 * fin.eps * SIGMA * ((T + th.ambient_c) / 2 + 273.15) ** 3
            G_out = (th.h_outside_w_m2k + h_rad) * A_out
            T = th.ambient_c + (q_internal + q_solar) / G_out
        G_in = th.h_inside_w_m2k * A_in
        return T + q_internal / G_in, 1 / (1 / G_in + 1 / G_out)

    # The pack is ~45 kg of cells: it takes hours to reach steady state, so the
    # check is its temperature at the end of a full mowing run, starting
    # heat-soaked from sitting in the sun.
    T_soak, _ = steady(aux.quiescent_w, q_sun)
    T_ss, G = steady(q_int, q_sun)
    tau_h = b.mass_kg * b.specific_heat_j_kgk / G / 3600
    run_h = r.values["mode_mowing_runtime_h"]
    T_end = T_soak + (T_ss - T_soak) * (1 - math.exp(-run_h / tau_h))
    T_chg, _ = steady(th.charge_current_a ** 2 * b.internal_resistance_mohm / 1000 + aux.quiescent_w, q_sun)
    r.add(
        Check(grp, "heat inside the box while mowing", round(q_int), "W",
              note=f"pack {q_pack:.0f} at {I:.0f} A, distribution {q_dist:.1f}, DC-DC {q_dcdc:.0f}, idle {aux.quiescent_w:g}"),
        Check(grp, f"solar load on lid ({p.enclosure.finish})", round(q_sun), "W"),
        Check(grp, "pack thermal time constant", round(tau_h, 1), "h", note=f"{b.mass_kg:g} kg x {b.specific_heat_j_kgk:g} J/kgK / {G:.1f} W/K"),
        Check(grp, f"pack temp after a full mowing run ({run_h:.1f} h) in sun at {th.ambient_c:g} C", round(T_end, 1), "C",
              b.max_temp_discharge_c, "<=", th.battery_margin_c / b.max_temp_discharge_c,
              note=f"starts heat-soaked at {T_soak:.0f} C; steady state if run forever: {T_ss:.0f} C"),
        Check(grp, "pack temp, parked in sun while charging", round(T_chg, 1), "C", b.max_temp_charge_c, "<=",
              th.battery_margin_c / b.max_temp_charge_c, note=f"{th.charge_current_a:g} A charge; charge in shade, let a hot pack cool first"),
    )


def structural(p, lay: Layout, r: Report):
    grp = "Box structure"
    g, ld, b = p.gauge, p.loads, p.battery
    allow = g.yield_mpa / ld.safety_factor
    allow_crash = g.yield_mpa / ld.crash_safety_factor
    W_bat = b.mass_kg * G0
    t = g.t

    # Floor under the pack: simply supported plate between the walls, pack
    # weight x vertical g spread over it (worst case: box held only at its edges).
    a, bb = lay.x.bat_x1 + lay.L_in / 2 + p.enclosure.bay_gap, lay.W_in
    a, bb = max(a, bb), min(a, bb)
    q = W_bat * ld.vertical_g / (a * bb)                    # N/mm^2
    sig = interp(a / bb, ROARK_RATIO, ROARK_BETA) * q * bb ** 2 / t ** 2
    defl = interp(a / bb, ROARK_RATIO, ROARK_ALPHA) * q * bb ** 4 / (g.E_mpa * t ** 3)
    r.add(Check(grp, f"floor bending under pack at {ld.vertical_g:g} g", round(sig, 1), "MPa", round(allow, 1), "<=", 0.1,
                note="if supported only at its edges; the frame rails under the floor make this much lower"),
          Check(grp, "floor deflection, same case", round(defl, 2), "mm", round(3 * t, 1), "<=",
                note="small-deflection theory; above ~t it over-predicts"))

    # Clamp bars: net uplift (vertical_g - 1) shared by the bars, load spread
    # over the pack width on a span between the two rods.
    c = p.battery_clamp
    span = 2 * _rod_y(p, lay)
    F_bar = W_bat * (ld.vertical_g - 1) / c.count
    M = F_bar / 4 * (span - b.width / 2)
    rod_load = c.rod_preload_n + F_bar / 2
    friction = c.pad_friction * (4 * c.rod_preload_n + W_bat) if c.count >= 2 else 0
    r.add(
        Check(grp, "clamp bar bending (uplift)", round(M / u_channel_Z(c.web, c.flange, t), 1), "MPa", round(allow, 1), "<=", 0.1),
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
    r.add(
        Check(grp, f"crash decel (top speed into obstacle, {ld.crash_stop_distance:g} mm crush)", round(n_crash, 1), "g",
              note="garden-tractor estimate; road-vehicle ECE R100 pulses are 10-28 g"),
        Check(grp, "battery stop upright bending (crash)", round(M_stop / (s.length * t ** 2 / 6), 1), "MPa",
              round(allow_crash, 1), "<=", 0.1),
        Check(grp, "battery stop rivet shear (crash)", round(F / s.rivets), "N", s.rivet_shear_n, "<=", 0.2,
              note="rivet shear rating is REF; verify"),
    )


def mass_cg(p, lay: Layout, r: Report):
    """Mass of fabricated parts + components; CG in the box frame."""
    items = lay.mass_items()
    m = sum(kg for _, kg, _ in items)
    cg = [sum(kg * c[i] for _, kg, c in items) / m for i in range(3)]
    sheet = sum(kg for name, kg, _ in items if name.startswith("PB-"))
    r.add(
        Check("Box mass", "sheet metal parts", round(sheet, 2), "kg"),
        Check("Box mass", "box with pack (excl. wiring/hardware)", round(m, 1), "kg"),
        Check("Box mass", "CG x / y / z in box frame", f"{cg[0]:.0f} / {cg[1]:.0f} / {cg[2]:.0f}", "mm",
              note="origin: centre of tray floor underside"),
    )
    r.values.update(box_mass=m)
