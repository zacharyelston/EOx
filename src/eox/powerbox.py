"""Power box layout: where the battery, motor and controller sit, and the sheet
metal parts sized around them.

Box frame: origin at the centre of the tray's outer floor face. x runs along
the battery with the motor bay at +x, y runs across with the motor shaft
exiting the +y wall, z is up.

    -x wall | stop | battery | stop | bulkhead | motor bay (motor, electrics, controller, fan) | +x wall
            |<---- sealed battery bay ---->|          |<--- ventilated "wet" bay: floor inlet, fan out --->|
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
    shape: str               # "box" or "cyl_y" (cylinder, axis along y)
    center: tuple[float, float, float]
    size: tuple              # box: (dx, dy, dz); cyl_y: (diameter, length)
    mass: float

    def bounds(self) -> tuple[float, float, float, float, float, float]:
        cx, cy, cz = self.center
        if self.shape == "cyl_y":
            d, length = self.size
            dx, dy, dz = d, length, d
        else:
            dx, dy, dz = self.size
        return cx - dx / 2, cx + dx / 2, cy - dy / 2, cy + dy / 2, cz - dz / 2, cz + dz / 2


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


def build(p) -> Layout:
    e, bat, mot, ctl, ele, bh, vn = p.enclosure, p.battery, p.motor, p.controller, p.electrics, p.bulkhead, p.vent
    g, gd = p.gauge, p.doubler_gauge
    t = g.t

    # ---- interior envelope ------------------------------------------------
    bay = max(mot.diameter, ctl.length, ele.length)
    gap = p.battery_stop.leg + bh.stop_clearance + bh.flange + bh.bay_clearance
    L_in = e.battery_end_clearance + bat.length + gap + bay + e.bay_end_clearance
    W_in = max(bat.width + 2 * e.wall_clearance,
               mot.length + gd.t + ctl.thickness + ele.width + 10)
    H_need = max(e.battery_pad + bat.height + bat.terminal_clearance,
                 e.floor_clearance + mot.diameter + 10,
                 ele.height + 10)
    L_out, W_out = L_in + 2 * t, W_in + 2 * t

    tray_h = e.tray_height
    cover_h = math.ceil(H_need + 2 * t + e.cover_overlap - tray_h)
    z_top = tray_h - e.cover_overlap + cover_h
    H_in = z_top - 2 * t
    x0 = -L_in / 2
    st = SimpleNamespace(
        bat_x0=x0 + e.battery_end_clearance,
        bat_x1=x0 + e.battery_end_clearance + bat.length,
    )
    st.bh_x = st.bat_x1 + p.battery_stop.leg + bh.stop_clearance       # bulkhead face, battery side
    st.bh_top = z_top - t - bh.top_gap
    st.bay_x0 = st.bh_x + bh.flange + bh.bay_clearance
    st.bay_cx = st.bay_x0 + bay / 2
    st.floor = t

    lay = Layout(t, L_in, W_in, H_in, L_out, W_out, z_top, tray_h, cover_h, z_top, x=st)

    # ---- bodies -------------------------------------------------------------
    bat_z0 = t + e.battery_pad
    lay.bodies.append(Body("battery", "box", ((st.bat_x0 + st.bat_x1) / 2, 0, bat_z0 + bat.height / 2),
                           (bat.length, bat.width, bat.height), bat.mass_kg))
    motor_face_y = W_in / 2 - gd.t                      # flange face on the doubler
    motor_z = t + e.floor_clearance + mot.diameter / 2
    lay.bodies.append(Body("motor", "cyl_y", (st.bay_cx, motor_face_y - mot.length / 2, motor_z),
                           (mot.diameter, mot.length), mot.mass_kg))
    ctl_z = t + 15 + ctl.width / 2
    lay.bodies.append(Body("controller", "box", (st.bay_cx, -W_in / 2 + ctl.thickness / 2, ctl_z),
                           (ctl.length, ctl.thickness, ctl.width), ctl.mass_kg))
    ele_y = -W_in / 2 + ctl.thickness + 5 + ele.width / 2
    lay.bodies.append(Body("electrics", "box", (st.bay_cx, ele_y, t + ele.height / 2),
                           (ele.length, ele.width, ele.height), ele.mass_kg))
    st.motor_x, st.motor_z = st.bay_cx, motor_z
    st.fan_z = z_top - vn.fan_drop
    lay.bodies.append(Body("fan", "box", (L_in / 2 - 12.5, vn.fan_y, st.fan_z),
                           (25, vn.fan_size, vn.fan_size), 0.12))

    # ---- parts --------------------------------------------------------------
    tray = _tray(p, lay)
    cover = _cover(p, lay)
    lay.placed += [Placed(tray), Placed(cover, (0, 0, z_top), (180, 0, 0))]

    doubler = _doubler(p, lay)
    lay.placed.append(Placed(doubler, (st.motor_x, W_out / 2 - t, motor_z), (90, 0, 0)))

    clamp = _clamp_bar(p, lay)
    bat_top = bat_z0 + bat.height
    for xb in _clamp_xs(p, lay):
        lay.placed.append(Placed(clamp, (xb, 0, bat_top), (0, 0, 90)))

    stop = _stop(p, lay)
    s = p.battery_stop
    lay.placed.append(Placed(stop, (st.bat_x1 + s.leg / 2, 0, t), (0, 0, 90)))
    lay.placed.append(Placed(stop, (st.bat_x0 - s.leg / 2, 0, t), (0, 0, -90)))

    # local u -> global y, v -> z, w (flange side) -> +x into the motor bay
    lay.placed.append(Placed(_bulkhead(p, lay), (st.bh_x, 0, (t + st.bh_top) / 2), [(90, 0, 0), (0, 0, 90)]))
    return lay


def _clamp_xs(p, lay) -> list[float]:
    c, st = p.battery_clamp, lay.x
    xs = [st.bat_x0 + c.end_inset, st.bat_x1 - c.end_inset]
    return xs[: c.count] if c.count <= 2 else xs


def _rod_y(p, lay) -> float:
    return p.battery.width / 2 + (lay.W_in / 2 - p.battery.width / 2) / 2


def _lid_screw_xs(p, lay) -> list[float]:
    """Long-side lid screws: spread along the battery bay, clear of the bulkhead."""
    e, st = p.enclosure, lay.x
    hi = st.bh_x - 20            # keep rivnut bodies clear of the bulkhead edge
    lo = -lay.L_out / 2 + 70
    n = e.lid_screws_per_long_side
    return [lo + i * (hi - lo) / (n - 1) for i in range(n)] if n > 1 else [0.0]


def _doubler_size(p) -> tuple[float, float]:
    m, e = p.motor, p.enclosure
    w = m.bolt_pcd + m.bolt_diameter + 2 * e.doubler_margin
    zmax = e.tray_height - 2 - p.gauge.t        # stay under the rim
    zmin = 2 * p.gauge.ossb                     # stay off the floor bend
    motor_z = p.gauge.t + e.floor_clearance + m.diameter / 2
    h = 2 * min(w / 2, motor_z - zmin, zmax - motor_z)
    return w, h


def _motor_bolts(p) -> list[tuple[float, float]]:
    m = p.motor
    r = m.bolt_pcd / 2
    return [(r * math.cos(math.radians(45 + i * 360 / m.bolt_count)),
             r * math.sin(math.radians(45 + i * 360 / m.bolt_count))) for i in range(m.bolt_count)]


def _tray(p, lay) -> FlangedPanel:
    e, m, c, ctl = p.enclosure, p.motor, p.battery_clamp, p.controller
    st, H = lay.x, lay.tray_h
    holes: list[Hole] = []
    screw_h = H - e.cover_overlap / 2

    # +y wall: motor spigot, bolt circle, lid screws
    holes.append(Hole("+v", st.motor_x, st.motor_z, m.pilot_diameter + 1, "motor spigot"))
    holes += [Hole("+v", st.motor_x + bx, st.motor_z + bz, m.bolt_diameter + 0.5, "motor bolt")
              for bx, bz in _motor_bolts(p)]
    for xs in _lid_screw_xs(p, lay):
        holes.append(Hole("+v", xs, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))
        holes.append(Hole("-v", xs, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))

    # -y wall: controller mounting (M6 rivnuts at the corners of its footprint)
    cz = lay.body("controller").center[2]
    for dx in (-1, 1):
        for dz in (-1, 1):
            holes.append(Hole("-v", st.motor_x + dx * (ctl.length / 2 - 12), cz + dz * (ctl.width / 2 - 12),
                              e.rivnut_hole_m6, "M6 rivnut, controller"))

    # +x end wall: cable glands; both end walls: one lid screw
    gz = lay.t + 60
    for i, d in enumerate(e.gland_holes):
        holes.append(Hole("+u", -lay.W_in / 2 + 70 + i * 60, gz, d, "cable gland"))
    holes.append(Hole("+u", 0, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))
    holes.append(Hole("-u", 0, screw_h, e.rivnut_hole_m5, "M5 rivnut, cover screw"))

    # floor: mounts, clamp-rod rivnuts, stop rivets
    mx, my = lay.L_out / 2 - e.mount_inset, lay.W_out / 2 - e.mount_inset
    holes += [Hole("base", sx * mx, sy * my, e.rivnut_hole_m8, "M8 rivnut, frame mount")
              for sx in (-1, 1) for sy in (-1, 1)]
    ry = _rod_y(p, lay)
    holes += [Hole("base", xb, sy * ry, e.rivnut_hole_m8, "M8 rivnut, clamp rod")
              for xb in _clamp_xs(p, lay) for sy in (-1, 1)]
    for x_leg in _stop_rivet_xs(p, lay):
        holes += [Hole("base", x_leg, y, e.rivet_hole, "rivet, battery stop") for y in _stop_rivet_ys(p)]
    holes += [Hole("base", st.bh_x + p.bulkhead.rivet_h, y, e.rivet_hole, "rivet, bulkhead")
              for y in _bulkhead_rivet_ys(p, lay)]
    holes += _inlet_slots(p, lay, [(h.s, h.h, h.d) for h in holes if h.face == "base"])

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
    v = p.vent
    holes.append(Hole("+u", -v.fan_y, v.fan_drop, v.fan_opening, "fan opening"))
    k = v.fan_hole_spacing / 2
    holes += [Hole("+u", -v.fan_y + a * k, v.fan_drop + b * k, v.fan_screw_hole, "fan screw")
              for a in (-1, 1) for b in (-1, 1)]
    flanges = {k: Hc for k in ("+v", "-v", "+u", "-u")}
    return FlangedPanel("PB-102", "Cover (upper shell)", A, B, p.gauge, flanges, holes,
                        corner_gap=e.corner_gap,
                        note="EPDM foam tape on the tray walls where the skirt overlaps.")


def _doubler(p, lay) -> FlangedPanel:
    m = p.motor
    w, h = _doubler_size(p)
    holes = [Hole("base", 0, 0, m.pilot_diameter + 1, "motor spigot")]
    holes += [Hole("base", bx, bz, m.bolt_diameter + 0.5, "motor bolt") for bx, bz in _motor_bolts(p)]
    return FlangedPanel("PB-103", "Motor doubler plate", w, h, p.doubler_gauge, {}, holes,
                        note="Laser only. Sandwiches the +y wall between motor flange and doubler.")


def _bulkhead(p, lay) -> FlangedPanel:
    bh, st, t = p.bulkhead, lay.x, lay.t
    zc = (t + st.bh_top) / 2
    holes = [Hole("-v", y, bh.rivet_h, p.enclosure.rivet_hole, "rivet to floor") for y in _bulkhead_rivet_ys(p, lay)]
    holes += [Hole("base", y, t + bh.gland_z - zc, d, "cable gland")
              for y, d in zip((-45, 45), bh.gland_holes)]
    return FlangedPanel("PB-106", "Bulkhead", lay.W_in - 2 * bh.side_gap, st.bh_top - t, p.gauge,
                        {k: bh.flange for k in ("+u", "-u", "+v", "-v")}, holes, corner_gap=p.enclosure.corner_gap,
                        note="Seals battery bay from motor bay: foam on side + top flanges.")


def _bulkhead_rivet_ys(p, lay) -> list[float]:
    n = p.bulkhead.rivets
    span = lay.W_in - 2 * p.bulkhead.side_gap - 60
    return [-span / 2 + i * span / (n - 1) for i in range(n)]


def _inlet_slots(p, lay, avoid: list[tuple[float, float, float]]) -> list[Hole]:
    """Floor inlet slots in the motor bay: under the motor and under the
    controller (the electrics plate sits on the floor between them). They face
    down, so they also drain the bay."""
    v, st, t = p.vent, lay.x, lay.t
    span = v.inlet_slot_length + v.inlet_slot_width
    x_lo, x_hi = st.bay_x0 + 5 + span / 2, lay.L_in / 2 - 12 - span / 2
    xs, x = [], x_lo
    while x <= x_hi + 1e-6:
        xs.append(x)
        x += v.inlet_pitch_x
    motor = lay.body("motor").bounds()
    ctl = lay.body("controller").bounds()
    bands = [(motor[2] + 5, lay.W_in / 2 - 15), (-lay.W_in / 2 + 15, ctl[3] - 5)]
    out = []
    for y0, y1 in bands:
        y = y0 + v.inlet_slot_width / 2
        while y <= y1 - v.inlet_slot_width / 2 + 1e-6:
            for x in xs:
                clear = all(abs(x - ax) > span / 2 + ad / 2 + 2 * t or abs(y - ay) > v.inlet_slot_width / 2 + ad / 2 + 2 * t
                            for ax, ay, ad in avoid)
                if clear:
                    out.append(Hole("base", x, y, v.inlet_slot_width, "inlet slot", length=v.inlet_slot_length))
            y += v.inlet_pitch_y
    return out


def _clamp_bar(p, lay) -> FlangedPanel:
    c = p.battery_clamp
    length = lay.W_in - 2 * c.end_clearance
    ry = _rod_y(p, lay)
    holes = [Hole("base", s * ry, 0, c.rod_diameter + 1, "M8 rod") for s in (-1, 1)]
    return FlangedPanel("PB-104", "Battery clamp bar", length, c.web, p.gauge,
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
    g, s = p.gauge, p.battery_stop
    return -s.leg / 2 + 2 * g.t + p.enclosure.rivet_hole / 2


def _stop_rivet_xs(p, lay) -> list[float]:
    st, s = lay.x, p.battery_stop
    v = _stop_rivet_v(p)
    # stop at +x end: Rot z +90 maps local v -> global -x ; at -x end: Rot z -90 maps v -> +x
    return [st.bat_x1 + s.leg / 2 - v, st.bat_x0 - s.leg / 2 + v]


def assembly(lay: Layout):
    """Every sheet metal part plus component envelopes, as labelled solids."""
    from build123d import Box, Cylinder, Pos

    items = []
    for i, pl in enumerate(lay.placed):
        s = pl.solid()
        s.label = f"{pl.part.part_no}-{i}"
        items.append(("sheet", s))
    for b in lay.bodies:
        if b.shape == "cyl_y":
            s = Pos(*b.center) * Cylinder(b.size[0] / 2, b.size[1], rotation=(90, 0, 0))
        else:
            s = Pos(*b.center) * Box(*b.size)
        s.label = b.name
        items.append((b.name, s))
    # motor shaft stub, outside the +y wall
    m = lay.body("motor")
    face_y = m.center[1] + m.size[1] / 2
    shaft_len = 45
    s = Pos(m.center[0], face_y + shaft_len / 2, m.center[2]) * Cylinder(19.05 / 2, shaft_len, rotation=(90, 0, 0))
    s.label = "shaft"
    items.append(("shaft", s))
    return items
