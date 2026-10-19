"""Shared constants, tables and helpers for the engineering checks."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from eox.checks import Check

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
ROARK_RATIO = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0, 4.0, 5.0, 1e9]
ROARK_BETA = [0.2874, 0.3762, 0.4530, 0.5172, 0.5688, 0.6102, 0.7134, 0.7410, 0.7476, 0.7500]
ROARK_ALPHA = [0.0444, 0.0616, 0.0770, 0.0906, 0.1017, 0.1110, 0.1335, 0.1400, 0.1417, 0.1421]


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    values: dict[str, float] = field(default_factory=dict)

    def add(self, *cs: Check):
        self.checks.extend(cs)

    def worst(self) -> str:
        order = ["FAIL", "WARN", "PASS", "INFO"]
        return min((c.status for c in self.checks), key=order.index, default="INFO")


def interp(x, xs, ys):
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            f = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + f * (ys[i + 1] - ys[i])
    return ys[-1]


def tractive_force(mass_kg: float, slope_deg: float, crr: float) -> float:
    """Steady force to move a vehicle up a slope: m g (sin th + Crr cos th)."""
    th = math.radians(slope_deg)
    return mass_kg * G0 * (math.sin(th) + crr * math.cos(th))


def pick_step(steps: list[float], need: float) -> float:
    """Smallest standard rating >= need (the largest one if none is big enough)."""
    return next((s for s in steps if s >= need), steps[-1])


def pick_awg(amps: float, derate: float = 1.0) -> str:
    """Smallest conductor whose (derated) 105 C ampacity carries `amps`."""
    return next((a for a, amp in AMPACITY_105C.items() if amp * derate >= amps), "2/0")


def pack_voltages(b) -> tuple[float, float, float]:
    """(min, nominal, max) pack voltage."""
    return b.cells_series * b.cell_min_v, b.cells_series * b.cell_nominal_v, b.cells_series * b.cell_max_v


def u_channel_Z(web: float, flange: float, t: float) -> float:
    """Section modulus (mm^3) of a U-channel, web horizontal, flanges up,
    bending about the horizontal axis. Square-corner approximation."""
    A_w, y_w = web * t, t / 2
    A_f, y_f = (flange - t) * t, t + (flange - t) / 2
    A = A_w + 2 * A_f
    yb = (A_w * y_w + 2 * A_f * y_f) / A
    I = (web * t ** 3 / 12 + A_w * (yb - y_w) ** 2
         + 2 * (t * (flange - t) ** 3 / 12 + A_f * (y_f - yb) ** 2))
    return I / max(yb, flange - yb)
