"""Tractor layout: where the axle modules, power box, pivot and operator sit.

Frame: origin on the ground under the pivot, x forward, y left, z up (mm).
Pro (articulated): each half is a rigid body; the front half articulates
(yaw) and oscillates (roll) about the pivot, and pitch is locked so the two
halves share pitch loads.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from eox import powerbox
from eox.powerbox import Body

HALVES = ("front", "rear")


@dataclass
class Mass:
    name: str
    kg: float
    cg: tuple[float, float, float]
    half: str


@dataclass
class Tractor:
    p: object
    box: powerbox.Layout
    box_pos: tuple[float, float, float]
    bodies: list[tuple[str, str, Body]] = field(default_factory=list)   # (half, kind, body)
    masses: list[Mass] = field(default_factory=list)

    # ---- geometry ----------------------------------------------------------
    @property
    def wheel_radius(self) -> float:
        return self.p.axle.tire_diameter / 2

    def axle_x(self, half: str) -> float:
        return self.p.layout.front_axle_x if half == "front" else self.p.layout.rear_axle_x

    def contacts(self, half: str, gamma_deg: float = 0.0) -> list[tuple[float, float, float]]:
        x, ty = self.axle_x(half), self.p.axle.track / 2
        return [self._yaw((x, s * ty, 0.0), half, gamma_deg) for s in (1, -1)]

    def joint(self) -> tuple[float, float, float]:
        return (0.0, 0.0, self.p.layout.pivot_height)

    @staticmethod
    def _yaw(pt, half: str, gamma_deg: float):
        """Articulate: the front half yaws by gamma about the pivot's vertical axis."""
        if half != "front" or not gamma_deg:
            return pt
        g = math.radians(gamma_deg)
        x, y, z = pt
        return (x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g), z)

    # ---- mass properties -----------------------------------------------------
    def mass(self, half: str | None = None) -> float:
        return sum(m.kg for m in self.masses if half in (None, m.half))

    def cg(self, half: str | None = None, gamma_deg: float = 0.0) -> tuple[float, float, float]:
        tot, acc = 0.0, [0.0, 0.0, 0.0]
        for m in self.masses:
            if half in (None, m.half):
                c = self._yaw(m.cg, m.half, gamma_deg)
                tot += m.kg
                acc = [a + m.kg * ci for a, ci in zip(acc, c)]
        return tuple(a / tot for a in acc)

    def axle_loads_n(self) -> dict[str, float]:
        """Static, level, straight: pitch is locked across the pivot, so the
        whole machine shares one CG for fore-aft load split."""
        W = self.mass() * 9.81
        xc = self.cg()[0]
        xf, xr = self.axle_x("front"), self.axle_x("rear")
        nf = W * (xc - xr) / (xf - xr)
        return {"front": nf, "rear": W - nf}

    # ---- preview -------------------------------------------------------------
    def assembly(self):
        from build123d import Pos
        items = []
        for half, kind, b in self.bodies:
            s = b.solid()
            s.label = f"{half}-{b.name}"
            items.append((kind, s))
        for kind, s in powerbox.assembly(self.box):
            s = Pos(*self.box_pos) * s
            s.label = f"box-{s.label}"
            items.append((kind, s))
        return items


def build_pro(p, box: powerbox.Layout | None = None) -> Tractor:
    box = box or powerbox.build(p)
    a, u, lo = p.axle, p.unit, p.layout
    r = a.tire_diameter / 2
    tr = Tractor(p, box, (lo.powerbox_x, 0.0, lo.powerbox_z))

    def add(half, kind, name, shape, center, size, kg=0.0):
        body = Body(name, shape, tuple(center), tuple(size), kg)
        tr.bodies.append((half, kind, body))
        if kg:
            tr.masses.append(Mass(name, kg, body.center, half))

    rail_z = r + 30 + 40                    # rails sit on the axle tubes
    for half in HALVES:
        x = tr.axle_x(half)
        s = 1 if half == "front" else -1    # outward direction from the pivot
        dl, dw = a.diff_size
        add(half, "wheel", "wheel L", "cyl_y", (x, a.track / 2, r), (a.tire_diameter, a.tire_width), a.wheel_tire_mass_kg)
        add(half, "wheel", "wheel R", "cyl_y", (x, -a.track / 2, r), (a.tire_diameter, a.tire_width), a.wheel_tire_mass_kg)
        add(half, "axle", "rear end", "box", (x, 0, r), (dl, dw, 2 * (r - a.diff_clearance)), a.rear_end_mass_kg)
        add(half, "axle", "axle tube", "cyl_y", (x, 0, r), (60, a.track - a.tire_width))
        mx = x - s * (dl / 2 + u.motor_length / 2)            # motor faces the pivot
        add(half, "motor", "drive unit motor", "cyl_x", (mx, 0, r), (u.motor_diameter, u.motor_length), u.motor_mass_kg)
        cl, cw, ct = u.controller_size
        add(half, "controller", "drive unit controller", "box", (mx, lo.frame_half_width + 20 + ct / 2, rail_z),
            (cl, ct, cw), u.controller_mass_kg)
        x0, x1 = sorted((s * lo.frame_end_x, x + s * 150))
        for side in (1, -1):
            add(half, "frame", f"rail {'L' if side > 0 else 'R'}", "box", ((x0 + x1) / 2, side * lo.frame_half_width, rail_z),
                (x1 - x0, 40, 80), a.subframe_mass_kg / 2)

    # pivot: vertical articulation pin + fore-aft oscillation pin
    add("rear", "pivot", "articulation pin", "cyl_z", (0, 0, lo.pivot_height), (70, 180), lo.joint_mass_kg)
    add("rear", "pivot", "oscillation pin", "cyl_x", (0, 0, lo.pivot_height), (50, 2 * lo.frame_end_x + 60))
    sx, sy, sz = lo.steering_cg
    add("rear", "steering", "steering cylinder", "cyl_x", (sx + 150, -p.steering.lever_arm, sz), (55, 500))
    tr.masses.append(Mass("steering", lo.steering_mass_kg, tuple(lo.steering_cg), "rear"))

    # front half: power box + implement face
    bx, by, bz = tr.box_pos
    for name, kg, (cx, cy, cz) in box.mass_items():
        tr.masses.append(Mass(f"box {name}", kg, (bx + cx, by + cy, bz + cz), "front"))
    add("front", "implement", "implement face", "box", (lo.implement_face_x, 0, 320), (12, 640, 260), lo.implement_mass_kg)

    # rear half: operator station
    sc = tuple(lo.seat_and_controls_cg)
    add("rear", "seat", "seat pan", "box", (lo.operator_cg[0] + 20, 0, 560), (420, 440, 70))
    add("rear", "seat", "seat back", "box", (lo.operator_cg[0] - 190, 0, 780), (60, 440, 420))
    add("rear", "seat", "steering column", "cyl_z", (lo.footrest_front_x + 60, 0, 620), (40, 420))
    add("rear", "frame", "footrest", "box", (lo.footrest_front_x - 110, 0, rail_z + 45), (220, 2 * lo.frame_half_width + 40, 10))
    tr.masses.append(Mass("seat & controls", lo.seat_and_controls_mass_kg, sc, "rear"))
    tr.masses.append(Mass("operator", p.vehicle.mass_operator_kg, tuple(lo.operator_cg), "rear"))
    if p.vehicle.mass_payload_kg:
        tr.masses.append(Mass("payload", p.vehicle.mass_payload_kg, sc, "rear"))
    return tr


BUILDERS = {"articulated": build_pro}


def build(p, box: powerbox.Layout | None = None) -> Tractor:
    try:
        return BUILDERS[p.model.layout](p, box)
    except KeyError:
        raise NotImplementedError(f"layout '{p.model.layout}' has no builder yet") from None
