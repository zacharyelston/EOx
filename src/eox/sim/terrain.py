"""The test course (design/course.toml) as a heightfield.

Obstacles are laid out along +x with flat gaps between; the centreline is
y = 0. Heights are in metres on a regular grid, z[iy, ix], ready for a MuJoCo
hfield (row 0 is the -y edge, column 0 the -x edge).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Segment:
    name: str
    kind: str
    x0: float            # m, where the obstacle starts ...
    x1: float            # ... and ends, along the course
    spec: object         # the [[course.obstacle]] entry


@dataclass
class Course:
    name: str
    length: float
    width: float
    res: float
    segments: list[Segment]
    xs: np.ndarray
    ys: np.ndarray
    z: np.ndarray        # [len(ys), len(xs)]

    def height(self, x: float, y: float) -> float:
        """Ground height under (x, y), bilinear like the heightfield's surface."""
        fx = np.clip((x - self.xs[0]) / self.res, 0, len(self.xs) - 1.000001)
        fy = np.clip((y - self.ys[0]) / self.res, 0, len(self.ys) - 1.000001)
        i, j = int(fy), int(fx)
        u, v = fx - j, fy - i
        z = self.z
        return float((1 - u) * (1 - v) * z[i, j] + u * (1 - v) * z[i, j + 1]
                     + (1 - u) * v * z[i + 1, j] + u * v * z[i + 1, j + 1])

    def centreline(self) -> tuple[np.ndarray, np.ndarray]:
        return self.xs, self.z[len(self.ys) // 2]


def _span(ob) -> float:
    k = ob.kind
    if k in ("bump", "step", "ditch"):
        return ob.length
    if k == "twist":
        return (ob.count - 1) * ob.pitch + ob.length
    if k == "ramp":
        return 2 * ob.rise / math.tan(math.radians(ob.slope_deg)) + ob.length
    if k == "side_slope":
        return 2 * ob.transition + ob.length
    raise ValueError(f"unknown obstacle kind '{k}'")


def _smooth(profile: np.ndarray, width_m: float, res: float) -> np.ndarray:
    """Moving average: turns each kink of a ramp into a vertical curve."""
    n = max(1, int(round(width_m / res)))
    if n < 2:
        return profile
    pad = np.pad(profile, n, mode="edge")
    return np.convolve(pad, np.ones(n) / n, mode="same")[n:-n]


def build(c) -> Course:
    """c: the [course] namespace from params.load()."""
    from eox.sim import detail
    res = detail(c).resolution
    x = c.run_in
    segs = []
    for ob in c.obstacle:
        span = _span(ob)
        segs.append(Segment(ob.name, ob.kind, x, x + span, ob))
        x += span + c.gap
    length = x - c.gap + c.run_out
    xs = np.arange(0.0, length + res / 2, res)
    ys = np.arange(-c.width / 2, c.width / 2 + res / 2, res)
    X, Y = np.meshgrid(xs, ys)
    z = np.zeros_like(X)
    for s in segs:
        ob, u = s.spec, xs - s.x0
        inside = (u >= 0) & (u <= s.x1 - s.x0)
        if s.kind in ("bump", "ditch"):
            sign = 1 if s.kind == "bump" else -1
            h = ob.height if s.kind == "bump" else ob.depth
            prof = np.where(inside, sign * h * 0.5 * (1 - np.cos(2 * math.pi * u / ob.length)), 0.0)
            z += prof[None, :]
        elif s.kind == "step":
            z += np.where(inside, ob.height, 0.0)[None, :]
        elif s.kind == "twist":
            r0 = ob.length / 2
            for k in range(ob.count):
                cx = s.x0 + r0 + k * ob.pitch
                cy = ob.offset * (1 if k % 2 == 0 else -1)
                r = np.hypot(X - cx, Y - cy)
                z += np.where(r < r0, ob.height * 0.5 * (1 + np.cos(math.pi * r / r0)), 0.0)
        elif s.kind == "ramp":
            g = math.tan(math.radians(ob.slope_deg))
            run = ob.rise / g
            prof = np.clip(np.minimum(u / run, (s.x1 - s.x0 - u) / run), 0.0, 1.0) * ob.rise
            prof = np.where(inside, prof, 0.0)
            z += _smooth(prof, ob.crest_radius * g, res)[None, :]
        elif s.kind == "side_slope":
            full = math.tan(math.radians(ob.slope_deg))
            T = ob.transition
            ramp = np.clip(np.minimum(u / T, (s.x1 - s.x0 - u) / T), 0.0, 1.0)
            tilt = np.where(inside, full * 0.5 * (1 - np.cos(math.pi * ramp)), 0.0)
            z += Y * tilt[None, :]                       # +y side rises: the slope falls to the right
    return Course(c.name, float(xs[-1]), float(ys[-1] - ys[0]), res, segs, xs, ys, z)
