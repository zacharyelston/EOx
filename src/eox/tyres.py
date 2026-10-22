"""Tyres on turf: deflection, stiffness, grip and rolling resistance from tyre
size, inflation pressure, wheel load and ground strength.

Deflection: an inflated tyre carries load on its contact patch. A plane
pressed delta into a tyre of diameter D and section width b cuts an ellipse
with semi-axes sqrt(D delta) and sqrt(b delta), so

    W = (p + p_carcass) * pi * delta * sqrt(D b)

and the tyre's vertical stiffness is k = (p + p_carcass) pi sqrt(D b).

Grip and rolling resistance on soil: Brixius (1987), adopted in ASAE D497.
The wheel mobility number

    Bn = (CI b d / W) * (1 + 5 delta/h) / (1 + 3 b/d)

(CI = ground cone index, h = section height) sets the gross traction ratio
and the motion resistance ratio at slip s:

    GTR = 0.88 (1 - e^(-0.1 Bn)) (1 - e^(-7.5 s)) + 0.04
    MRR = 1/Bn + 0.04 + 0.5 s / sqrt(Bn)

A softer tyre deflects more, raising Bn: more grip, less rolling resistance,
the more so on soft ground. The equations are empirical (bias-ply tractor
tyres, 1970s-80s data) and known to under-predict pressure effects, so read
results as comparisons between pressures, not absolute values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

G = 9.81


@dataclass
class Tyre:
    diameter: float      # mm
    width: float         # mm, section width
    rim: float           # mm, rim diameter
    pressure_kpa: float

    @property
    def section_height(self) -> float:
        return (self.diameter - self.rim) / 2


def stiffness(t: Tyre, ground) -> float:
    """Vertical stiffness, N/m."""
    return (t.pressure_kpa + ground.carcass_kpa) * 1000 * math.pi * math.sqrt(t.diameter / 1000 * t.width / 1000)


def deflection(t: Tyre, load_n: float, ground) -> float:
    """Static deflection under load, mm."""
    return max(load_n, 0.0) / stiffness(t, ground) * 1000


def mobility(t: Tyre, load_n: float, ground) -> float:
    W = max(load_n, 1.0)
    d, b = t.diameter / 1000, t.width / 1000
    delta_h = deflection(t, W, ground) / t.section_height
    return ground.cone_index_kpa * 1000 * b * d / W * (1 + 5 * delta_h) / (1 + 3 * b / d)


def grip(t: Tyre, load_n: float, ground, slip: float | None = None) -> float:
    """Gross traction ratio at the design slip: the most the tyre pulls per unit load."""
    s = ground.design_slip if slip is None else slip
    Bn = mobility(t, load_n, ground)
    return 0.88 * (1 - math.exp(-0.1 * Bn)) * (1 - math.exp(-7.5 * s)) + 0.04


def rolling(t: Tyre, load_n: float, ground) -> float:
    """Motion resistance ratio, free rolling."""
    return 1 / mobility(t, load_n, ground) + 0.04


def of_axle(ax) -> Tyre:
    return Tyre(ax.tire_diameter, ax.tire_width, ax.rim, ax.pressure_kpa)


def apply(p, tr) -> dict:
    """Each axle's tyres at their static load (deck fitted, with operator), and
    the machine-level grip and rolling resistance the calcs use. Returns the
    per-axle numbers (also kept on the Tractor as tr.tyres)."""
    from eox.tractor import DECK

    gr = p.ground
    loads = tr.axle_loads_n(fitted=DECK)
    out = {}
    for ax in tr.axles:
        t = of_axle(ax)
        W = loads[ax.name] / 2
        out[ax.name] = dict(tyre=t, load_n=W, grip=grip(t, W, gr), rolling=rolling(t, W, gr),
                            deflection_mm=deflection(t, W, gr), deflection_ratio=deflection(t, W, gr) / t.section_height,
                            stiffness=stiffness(t, gr), mobility=mobility(t, W, gr))
    drive = [ax.name for ax in tr.axles if ax.driven]
    p.vehicle.traction_coefficient = sum(out[n]["grip"] * loads[n] for n in drive) / sum(loads[n] for n in drive)
    p.vehicle.rolling_resistance = sum(out[n]["rolling"] * loads[n] for n in out) / sum(loads.values())
    tr.tyres = out
    return out
