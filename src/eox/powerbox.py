"""Battery & distribution box: where the pack and the bus hardware sit, and the
sheet metal parts sized around them.

Box frame: origin at the centre of the tray's outer floor face, x along the
battery with the distribution bay at +x, y across, z up.

    -x wall | stop | battery | stop | distribution bay (fuses, contactor, DC-DC) | +x wall: unit branch glands
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import SimpleNamespace

from eox.sheetmetal import FlangedPanel, Hole


@dataclass
class Body:
    """A bought component's envelope, for fit checks, CG and the preview."""
    name: str
    shape: str               # "box", "cyl_x", "cyl_y" or "cyl_z" (cylinder axis)
    center: tuple[float, float, float]
    size: tuple              # box: (dx, dy, dz); cylinder: (diameter, length)
    mass: float = 0.0

    def bounds(self) -> tuple[float, float, float, float, float, float]:
        cx, cy, cz = self.center
        if self.shape.startswith("cyl"):
            d, length = self.size
            dx, dy, dz = {"cyl_x": (length, d, d), "cyl_y": (d, length, d), "cyl_z": (d, d, length)}[self.shape]
        else:
            dx, dy, dz = self.size
        return cx - dx / 2, cx + dx / 2, cy - dy / 2, cy + dy / 2, cz - dz / 2, cz + dz / 2

    def solid(self):
        from build123d import Box, Cylinder, Pos
        if self.shape == "box":
            return Pos(*self.center) * Box(*self.size)
        rot = {"cyl_x": (0, 90, 0), "cyl_y": (90, 0, 0), "cyl_z": (0, 0, 0)}[self.shape]
        return Pos(*self.center) * Cylinder(self.size[0] / 2, self.size[1], rotation=rot)


@dataclass
class Placed:
    part: FlangedPanel
    pos: tuple[float, float, float] = (0, 0, 0)
    rot: tuple = (0, 0, 0)   # build123d Rot(x, y, z), or a list of them applied first-to-last

    def solid(self):
        from build123d import Pos, Rot
        rots = [self.rot] if isinstance(self.rot[0], (int, float)) else list(self.rot)
        s = self.part.solid()
        for r in rots:
            s = Rot(*r) * s
        return Pos(*self.pos) * s


@dataclass
class Layout:
    t: float
    L_in: float
    W_in: float
    H_in: float
    L_out: float
    W_out: float
    H_out: float
    tray_h: float
    cover_h: float
    z_top: float                       # cover outer top face
    bodies: list[Body] = field(default_factory=list)
    placed: list[Placed] = field(default_factory=list)
    x: SimpleNamespace = field(default_factory=SimpleNamespace)   # named stations

    def body(self, name: str) -> Body:
        return next(b for b in self.bodies if b.name == name)

    def part(self, part_no: str) -> FlangedPanel:
        return next(p.part for p in self.placed if p.part.part_no == part_no)

    @property
    def parts(self) -> list[FlangedPanel]:
        seen, out = set(), []
        for p in self.placed:
            if p.part.part_no not in seen:
                seen.add(p.part.part_no)
                out.append(p.part)
        return out

    @property
    def outer(self) -> tuple[float, float, float]:
        """Outer size with the cover on: L, W, H."""
        c = self.part("PB-102")
        return c.A, c.B, self.H_out

    def mass_items(self) -> list[tuple[str, float, tuple[float, float, float]]]:
        """(name, kg, CG in box frame) for every body and sheet part."""
        items = [(b.name, b.mass, b.center) for b in self.bodies]
        for pl in self.placed:
            c = pl.solid().bounding_box().center()
            items.append((pl.part.part_no, pl.part.mass_kg(), (c.X, c.Y, c.Z)))
        return items


def build(p) -> Layout:
    e, bat, dist = p.enclosure, p.battery, p.distribution
    t = p.gauge.t

    # ---- interior envelope ------------------------------------------------
    L_in = e.battery_end_clearance + bat.length + e.bay_gap + dist.length + e.bay_end_clearance
    W_in = max(bat.width + 2 * e.wall_clearance, dist.width + 20)
    H_need = max(e.battery_pad + bat.height + bat.terminal_clearance, dist.height + 10)
    L_out, W_out = L_in + 2 * t, W_in + 2 * t

    tray_h = e.tray_height
    cover_h = math.ceil(H_need + 2 * t + e.cover_overlap - tray_h)
    z_top = tray_h - e.cover_overlap + cover_h
    H_in = z_top - 2 * t
    st = SimpleNamespace(bat_x0=-L_in / 2 + e.battery_end_clearance)
    st.bat_x1 = st.bat_x0 + bat.length
    st.bay_x0 = st.bat_x1 + e.bay_gap
    st.floor = t

    lay = Layout(t, L_in, W_in, H_in, L_out, W_out, z_top, tray_h, cover_h, z_top, x=st)

    # ---- bodies -------------------------------------------------------------
    bat_z0 = t + e.battery_pad
    lay.bodies.append(Body("battery", "box", ((st.bat_x0 + st.bat_x1) / 2, 0, bat_z0 + bat.height / 2),
                           (bat.length, bat.width, bat.height), bat.mass_kg))
    lay.bodies.append(Body("distribution", "box", (st.bay_x0 + dist.length / 2, 0, t + dist.height / 2),
                           (dist.length, dist.width, dist.height), dist.mass_kg))

    # ---- parts --------------------------------------------------------------
    lay.placed += [Placed(_tray(p, lay)), Placed(_cover(p, lay), (0, 0, z_top), (180, 0, 0))]
    clamp = _clamp_bar(p, lay)
    for xb in _clamp_xs(p, lay):
        lay.placed.append(Placed(clamp, (xb, 0, bat_z0 + bat.height), (0, 0, 90)))
    stop = _stop(p, lay)
    s = p.battery_stop
    lay.placed.append(Placed(stop, (st.bat_x1 + s.leg / 2, 0, t), (0, 0, 90)))
    lay.placed.append(Placed(stop, (st.bat_x0 - s.leg / 2, 0, t), (0, 0, -90)))
    return lay


def _clamp_xs(p, lay) -> list[float]:
    c, st = p.battery_clamp, lay.x
    xs = [st.bat_x0 + c.end_inset, st.bat_x1 - c.end_inset]
    return xs[: c.count] if c.count <= 2 else xs


def _rod_y(p, lay) -> float:
    return p.battery.width / 2 + (lay.W_in / 2 - p.battery.width / 2) / 2


def _lid_screw_xs(p, lay) -> list[float]:
    n = p.enclosure.lid_screws_per_long_side
    lo, hi = -lay.L_out / 2 + 70, lay.L_out / 2 - 70
    return [lo + i * (hi - lo) / (n - 1) for i in range(n)] if n > 1 else [0.0]


def _spread(n: int, pitch: float) -> list[float]:
    return [(i - (n - 1) / 2) * pitch for i in range(n)]


def _tray(p, lay) -> FlangedPanel:
    e, H = p.enclosure, lay.tray_h
    holes: list[Hole] = []
    screw_h = H - e.cover_overlap / 2

    for xs in _lid_screw_xs(p, lay):
        holes.append(Hole("+v", xs, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))
        holes.append(Hole("-v", xs, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))
    holes.append(Hole("+u", 0, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))
    holes.append(Hole("-u", 0, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))

    # +x end wall: one big gland per unit branch (low row), small glands above
    n = p.bus.units_installed
    holes += [Hole("+u", y, lay.t + 35, e.branch_gland_hole, "unit branch gland")
              for y in _spread(n, (lay.W_in - 100) / max(n - 1, 1))]
    holes += [Hole("+u", y, lay.t + 82, d, "gland")
              for y, d in zip(_spread(len(e.gland_holes), 70), e.gland_holes)]

    # floor: frame mounts, clamp-rod rivnuts, stop rivets
    mx, my = lay.L_out / 2 - e.mount_inset, lay.W_out / 2 - e.mount_inset
    holes += [Hole("base", sx * mx, sy * my, e.rivnut_hole_m8, "M8 rivnut, frame mount")
              for sx in (-1, 1) for sy in (-1, 1)]
    ry = _rod_y(p, lay)
    holes += [Hole("base", xb, sy * ry, e.rivnut_hole_m8, "M8 rivnut, clamp rod")
              for xb in _clamp_xs(p, lay) for sy in (-1, 1)]
    for x_leg in _stop_rivet_xs(p, lay):
        holes += [Hole("base", x_leg, y, e.rivet_hole, "rivet, battery stop") for y in _stop_rivet_ys(p)]

    flanges = {k: H for k in ("+v", "-v", "+u", "-u")}
    return FlangedPanel("PB-101", "Tray (lower shell)", lay.L_out, lay.W_out, p.gauge, flanges, holes,
                        corner_gap=e.corner_gap,
                        note="Seal the four corner reliefs with MS-polymer after assembly.")


def _cover(p, lay) -> FlangedPanel:
    e = p.enclosure
    clr = e.cover_fit_clearance + lay.t
    A, B, Hc = lay.L_out + 2 * clr, lay.W_out + 2 * clr, lay.cover_h
    h_screw = lay.z_top - (lay.tray_h - e.cover_overlap / 2)
    holes = []
    # cover is flipped 180 deg about x: local +v faces global -y, local s on u-edges = -global y
    for xs in _lid_screw_xs(p, lay):
        holes.append(Hole("+v", xs, h_screw, e.lid_screw_hole, "M5 cover screw"))
        holes.append(Hole("-v", xs, h_screw, e.lid_screw_hole, "M5 cover screw"))
    holes.append(Hole("+u", 0, h_screw, e.lid_screw_hole, "M5 cover screw"))
    holes.append(Hole("-u", 0, h_screw, e.lid_screw_hole, "M5 cover screw"))
    holes.append(Hole("-u", -60, 30, e.breather_hole, "M12 breather vent"))
    flanges = {k: Hc for k in ("+v", "-v", "+u", "-u")}
    return FlangedPanel("PB-102", "Cover (upper shell)", A, B, p.gauge, flanges, holes,
                        corner_gap=e.corner_gap,
                        note="EPDM foam tape on the tray walls where the skirt overlaps.")


def _clamp_bar(p, lay) -> FlangedPanel:
    c = p.battery_clamp
    ry = _rod_y(p, lay)
    holes = [Hole("base", s * ry, 0, c.rod_diameter + 1, "M8 rod") for s in (-1, 1)]
    return FlangedPanel("PB-104", "Battery clamp bar", lay.W_in - 2 * c.end_clearance, c.web, p.gauge,
                        {"+v": c.flange, "-v": c.flange}, holes, qty=c.count)


def _stop(p, lay) -> FlangedPanel:
    s = p.battery_stop
    holes = [Hole("base", y, _stop_rivet_v(p), p.enclosure.rivet_hole, "rivet") for y in _stop_rivet_ys(p)]
    return FlangedPanel("PB-105", "Battery stop angle", s.length, s.leg, p.gauge, {"+v": s.height}, holes,
                        qty=s.count)


def _stop_rivet_ys(p) -> list[float]:
    s = p.battery_stop
    span = s.length - 40
    return [-span / 2 + i * span / (s.rivets - 1) for i in range(s.rivets)]


def _stop_rivet_v(p) -> float:
    """Rivet line on the stop's floor leg: as far from the bend as edge distance allows."""
    return -p.battery_stop.leg / 2 + 2 * p.gauge.t + p.enclosure.rivet_hole / 2


def _stop_rivet_xs(p, lay) -> list[float]:
    st, s = lay.x, p.battery_stop
    v = _stop_rivet_v(p)
    # stop at +x end: Rot z +90 maps local v -> global -x ; at -x end: Rot z -90 maps v -> +x
    return [st.bat_x1 + s.leg / 2 - v, st.bat_x0 - s.leg / 2 + v]


def assembly(lay: Layout):
    """Every sheet metal part plus component envelopes, as labelled solids."""
    items = []
    for i, pl in enumerate(lay.placed):
        s = pl.solid()
        s.label = f"{pl.part.part_no}-{i}"
        items.append(("sheet", s))
    for b in lay.bodies:
        s = b.solid()
        s.label = b.name
        items.append((b.name, s))
    return items
