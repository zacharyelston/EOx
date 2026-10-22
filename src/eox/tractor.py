"""Tractor layout: where the axles, power box, operator and (Pro) pivot sit.

Bodies and masses belong to rigid *groups*:
  Pro  (articulated): "front" and "rear" halves. The front half yaws about
       the pivot's vertical pin and rolls on the oscillation trunnion; pitch
       is locked, so the halves share fore-aft loads.
  Home (steer axle):  one "chassis".
Frame: x forward, y left, z up from the ground (mm). Pro origin: under the
pivot. Home origin: under the rear axle.
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
    group: str
    tag: str = ""            # "" = always on the machine; otherwise an attachment ("deck") counted only when fitted


DECK = ("deck",)             # pass as `fitted` for the mowing configuration


@dataclass
class Axle:
    name: str            # "front" | "rear"
    x: float
    track: float
    tire_diameter: float
    tire_width: float
    group: str
    driven: bool
    clearance: float     # ground to the axle's lowest point
    rim: float = 203.0   # mm, rim diameter
    pressure_kpa: float = 83.0


@dataclass
class Link:
    """A part joining two groups (the Pro steering cylinder): drawn between anchors."""
    name: str
    kind: str
    a: tuple[float, float, float]
    a_group: str
    b: tuple[float, float, float]
    b_group: str
    diameter: float


@dataclass
class Tractor:
    p: object
    box: powerbox.Layout
    box_pos: tuple[float, float, float]
    box_group: str
    articulated: bool
    axles: list[Axle] = field(default_factory=list)
    bodies: list[tuple[str, str, Body]] = field(default_factory=list)   # (group, kind, body)
    masses: list[Mass] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    tyres: dict = field(default_factory=dict)         # per axle, from eox.tyres.apply

    # ---- geometry ----------------------------------------------------------
    def axle(self, name: str) -> Axle:
        return next(a for a in self.axles if a.name == name)

    @property
    def drive_units(self) -> int:
        return sum(a.driven for a in self.axles)

    def contacts(self, axle: str, gamma_deg: float = 0.0) -> list[tuple[float, float, float]]:
        a = self.axle(axle)
        return [self._yaw((a.x, s * a.track / 2, 0.0), a.group, gamma_deg) for s in (1, -1)]

    def joint(self) -> tuple[float, float, float]:
        return (0.0, 0.0, self.p.layout.pivot_height)

    def _yaw(self, pt, group: str, gamma_deg: float):
        """Articulate: the front half yaws by gamma about the pivot's vertical axis."""
        if not self.articulated or group != "front" or not gamma_deg:
            return pt
        g = math.radians(gamma_deg)
        x, y, z = pt
        return (x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g), z)

    # ---- mass properties -----------------------------------------------------
    # `fitted` lists the attachments on the machine (e.g. DECK); untagged masses
    # are always counted.
    def _counted(self, group, fitted):
        return [m for m in self.masses if group in (None, m.group) and (not m.tag or m.tag in fitted)]

    def mass(self, group: str | None = None, fitted: tuple = ()) -> float:
        return sum(m.kg for m in self._counted(group, fitted))

    def cg(self, group: str | None = None, gamma_deg: float = 0.0, fitted: tuple = ()) -> tuple[float, float, float]:
        tot, acc = 0.0, [0.0, 0.0, 0.0]
        for m in self._counted(group, fitted):
            c = self._yaw(m.cg, m.group, gamma_deg)
            tot += m.kg
            acc = [a + m.kg * ci for a, ci in zip(acc, c)]
        return tuple(a / tot for a in acc)

    def axle_loads_n(self, slope_deg: float = 0.0, fitted: tuple = ()) -> dict[str, float]:
        """Static axle loads, straight; on a fore-aft slope (climbing, positive)
        load moves to the rear axle by W sin(th) h / L. Pitch is rigid on both
        models (the Pro pivot locks pitch)."""
        W = self.mass(fitted=fitted) * 9.81
        xc, _, zc = self.cg(fitted=fitted)
        f, r = self.axle("front"), self.axle("rear")
        L = f.x - r.x
        th = math.radians(slope_deg)
        nf = W * (math.cos(th) * (xc - r.x) - math.sin(th) * zc) / L
        return {"front": nf, "rear": W * math.cos(th) - nf}

    # ---- preview -------------------------------------------------------------
    def assembly(self, gamma_deg: float = 0.0):
        """Labelled solids for the preview; the Pro front half articulated by gamma."""
        from build123d import Cylinder, Pos, Rot
        yaw = Rot(0, 0, gamma_deg if self.articulated else 0.0)
        items = []
        for group, kind, b in self.bodies:
            s = b.solid()
            if group == "front" and self.articulated:
                s = yaw * s
            s.label = f"{group}-{b.name}"
            items.append((kind, s))
        for kind, s in powerbox.assembly(self.box):
            s = Pos(*self.box_pos) * s
            if self.box_group == "front" and self.articulated:
                s = yaw * s
            s.label = f"box-{s.label}"
            items.append((kind, s))
        for ln in self.links:
            a = self._yaw(ln.a, ln.a_group, gamma_deg)
            b = self._yaw(ln.b, ln.b_group, gamma_deg)
            dx, dy, dz = (b[i] - a[i] for i in range(3))
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
            s = (Pos(*((a[i] + b[i]) / 2 for i in range(3))) * Rot(0, 0, math.degrees(math.atan2(dy, dx)))
                 * Rot(0, -pitch, 0) * Cylinder(ln.diameter / 2, length, rotation=(0, 90, 0)))
            s.label = f"link-{ln.name}"
            items.append((ln.kind, s))
        return items


class _Builder:
    def __init__(self, tr: Tractor):
        self.tr = tr

    def add(self, group, kind, name, shape, center, size, kg=0.0, tag=""):
        body = Body(name, shape, tuple(center), tuple(size), kg)
        self.tr.bodies.append((group, kind, body))
        if kg:
            self.tr.masses.append(Mass(name, kg, body.center, group, tag))
        return body

    def mass(self, group, name, kg, cg):
        self.tr.masses.append(Mass(name, kg, tuple(cg), group))

    def deck(self, group):
        """Mower deck + its PTO unit (a 3 HP unit standing on the deck, shaft
        down), tagged so the checks count them only when the deck is fitted."""
        d, u = self.tr.p.deck, self.tr.p.unit
        z0 = d.bottom_clearance
        self.add(group, "deck", "mower deck", "box", (d.x_center, 0, z0 + d.housing_height / 2),
                 (d.length, d.width, d.housing_height), d.mass_kg, tag="deck")
        top = z0 + d.housing_height
        self.add(group, "pto", "PTO unit motor", "cyl_z", (d.x_center, d.pto_unit_y, top + u.motor_length / 2),
                 (u.motor_diameter, u.motor_length), u.motor_mass_kg, tag="deck")
        self.tr.masses.append(Mass("PTO unit controller", u.controller_mass_kg,
                                   (d.x_center - 200, d.pto_unit_y, top + 50), group, "deck"))

    def drive_axle(self, group: str, name: str, x: float, outward: int, rail_z: float):
        """Golf-cart rear end + 3 HP unit. The gear case sits off-centre; the
        motor axis is parallel to the axle, on the gear case's side face, above
        the axle centre, running out over the longer tube. The controller lies
        flat on a cross member on the `outward` side (+1/-1 in x)."""
        p, a, u = self.tr.p, self.tr.p.axle, self.tr.p.unit
        r = a.tire_diameter / 2
        dl, dw = a.diff_size
        self.add(group, "wheel", "wheel L", "cyl_y", (x, a.track / 2, r), (a.tire_diameter, a.tire_width), a.wheel_tire_mass_kg)
        self.add(group, "wheel", "wheel R", "cyl_y", (x, -a.track / 2, r), (a.tire_diameter, a.tire_width), a.wheel_tire_mass_kg)
        self.add(group, "axle", "rear end", "box", (x, a.diff_offset_y, r), (dl, dw, 2 * (r - a.diff_clearance)),
                 a.rear_end_mass_kg)
        self.add(group, "axle", "axle tube", "cyl_y", (x, 0, r), (60, a.track - a.tire_width))
        y0 = a.diff_offset_y + dw / 2                                  # gear case side face
        self.add(group, "motor", "drive unit motor", "cyl_y",
                 (x + a.motor_offset_x, y0 + u.motor_length / 2, r + a.motor_offset_z),
                 (u.motor_diameter, u.motor_length), u.motor_mass_kg)
        cl, cw, ct = u.controller_size
        cx = x + outward * (dl / 2 + 20 + cw / 2)
        self.add(group, "controller", "drive unit controller", "box", (cx, 0, rail_z), (cw, cl, ct), u.controller_mass_kg)
        self.tr.axles.append(Axle(name, x, a.track, a.tire_diameter, a.tire_width, group, True, a.diff_clearance,
                                  a.tire_rim, a.tire_pressure_kpa))
        return cx

    def rails(self, group, x0, x1, rail_z, half_width, kg, name="rail"):
        x0, x1 = sorted((x0, x1))
        depth = getattr(self.tr.p.layout, "rail_depth_mm", 80)
        for side in (1, -1):
            self.add(group, "frame", f"{name} {'L' if side > 0 else 'R'}", "box", ((x0 + x1) / 2, side * half_width, rail_z),
                     (x1 - x0, 40, depth), kg / 2)

    def cross(self, group, name, x, rail_z, half_width, kg=0.0):
        self.add(group, "frame", name, "box", (x, 0, rail_z), (40, 2 * half_width + 40, 80), kg)

    def box_masses(self, group):
        bx, by, bz = self.tr.box_pos
        for name, kg, (cx, cy, cz) in self.tr.box.mass_items():
            self.mass(group, f"box {name}", kg, (bx + cx, by + cy, bz + cz))


def build_pro(p, box: powerbox.Layout | None = None) -> Tractor:
    """Articulated AWD: one drive-axle module per half, centre pivot."""
    box = box or powerbox.build(p)
    a, lo, st = p.axle, p.layout, p.steering
    tr = Tractor(p, box, (lo.powerbox_x, 0.0, lo.powerbox_z), "front", articulated=True)
    B = _Builder(tr)
    r = a.tire_diameter / 2
    rail_z = r + 30 + 40                     # rails sit on the axle tubes
    hw, e = lo.frame_half_width, lo.frame_end_x

    # each half: wide rails around its axle, necking in to the hinge zone so
    # the halves can swing past each other
    nx, nw = lo.neck_x, lo.neck_half_width
    for group, x, s in (("rear", lo.rear_axle_x, -1), ("front", lo.front_axle_x, 1)):
        B.drive_axle(group, group, x, s, rail_z)                      # controller outboard
        B.rails(group, s * nx, x + s * lo.frame_overhang, rail_z, hw, a.subframe_mass_kg * 0.7)
        for side in (1, -1):
            B.add(group, "frame", f"neck {'L' if side > 0 else 'R'}", "box", (s * (e + nx) / 2, side * nw, rail_z),
                  (nx - e, 20, 80), a.subframe_mass_kg * 0.15)
        B.cross(group, "hinge cross member", s * (e + 20), rail_z, nw)
        B.cross(group, "neck cross member", s * nx, rail_z, hw)
        B.cross(group, "outer cross member", x + s * (lo.frame_overhang - 20), rail_z, hw)

    # centre joint: front-half clevis ears at the upper and lower pins; the
    # knuckle between them yaws with the rear half and carries the fore-aft
    # roll trunnion into it (docs/research/articulation.md)
    ph, pd, sp, kw = lo.pivot_height, lo.pin_diameter, lo.pin_spacing, lo.knuckle_width
    for z, nm in ((ph + sp / 2, "upper"), (ph - sp / 2, "lower")):
        B.add("front", "pivot", f"clevis ear, {nm}", "box", ((e - 40) / 2, 0, z), (e + 40, kw + 40, lo.ear_thickness))
        B.add("front", "pivot", f"pin, {nm}", "cyl_z", (0, 0, z), (pd, lo.ear_thickness + 30))
    B.add("rear", "pivot", "knuckle", "box", (-(e - 40) / 2, 0, ph), (e + 40, kw, sp - lo.ear_thickness - 6),
          lo.joint_mass_kg)
    B.add("rear", "pivot", "roll trunnion", "cyl_x", (-(e + 20), 0, ph), (80, 100))
    ax = lo.knuckle_anchor_x
    B.add("rear", "pivot", "knuckle steering arm", "box", (ax, -(kw / 2 + st.lever_arm) / 2, rail_z),
          (40, st.lever_arm - kw / 2 + 20, 30))

    # steering cylinder: front-frame bracket to the knuckle arm (pure yaw, no roll input)
    ay = -st.lever_arm
    B.add("front", "frame", "cylinder bracket", "box", (lo.cylinder_anchor_x, -(nw + st.lever_arm) / 2, rail_z),
          (40, nw - st.lever_arm + 20, 40))
    tr.links.append(Link("steering cylinder", "steering", (ax, ay, rail_z), "rear",
                         (lo.cylinder_anchor_x, ay, rail_z), "front", st.bore + 15))
    B.mass("rear", "steering", lo.steering_mass_kg, lo.steering_cg)

    # front half: power box + implement face, and the front-mount deck when fitted
    B.box_masses("front")
    B.add("front", "implement", "implement face", "box", (lo.implement_face_x, 0, 320), (12, 640, 260), lo.implement_mass_kg)
    B.deck("front")

    # rear half: operator station
    oc = lo.operator_cg
    B.add("rear", "seat", "seat pan", "box", (oc[0] + 20, 0, 560), (420, 440, 70))
    B.add("rear", "seat", "seat back", "box", (oc[0] - 190, 0, 780), (60, 440, 420))
    B.add("rear", "seat", "steering column", "cyl_z", (lo.footrest_front_x + 60, 0, 620), (40, 420))
    B.add("rear", "frame", "footrest", "box", (lo.footrest_front_x - 110, 0, rail_z + 45), (220, 2 * hw + 40, 10))
    B.mass("rear", "seat & controls", lo.seat_and_controls_mass_kg, lo.seat_and_controls_cg)
    B.mass("rear", "operator", p.vehicle.mass_operator_kg, oc)
    if p.vehicle.mass_payload_kg:
        B.mass("rear", "payload", p.vehicle.mass_payload_kg, lo.seat_and_controls_cg)
    return tr


def build_home(p, box: powerbox.Layout | None = None) -> Tractor:
    """Conventional 2WD: golf-cart front steering axle, one drive-axle module at the rear."""
    box = box or powerbox.build(p)
    if hasattr(p, "kit"):
        from eox.kit_sim import prepare
        prepare(p)
    a, f, lo = p.axle, p.steer_axle, p.layout
    tr = Tractor(p, box, (lo.powerbox_x, 0.0, lo.powerbox_z), "chassis", articulated=False)
    B = _Builder(tr)
    r = a.tire_diameter / 2
    depth = getattr(lo, "rail_depth_mm", 80)
    rail_z = r + 30 + depth / 2
    hw = lo.frame_half_width
    xr, xf = 0.0, lo.wheelbase

    B.drive_axle("chassis", "rear", xr, -1, rail_z)           # controller behind the axle
    # main rails wide around the rear axle and box; a narrow nose clears the steered wheels.
    # Rail mass follows rail length, so a longer frame (e.g. to hang the box out front) weighs more.
    main, nose = lo.nose_x - (xr - lo.rear_overhang), xf + lo.front_overhang - lo.nose_x
    B.rails("chassis", xr - lo.rear_overhang, lo.nose_x, rail_z, hw, 2 * main / 1000 * lo.rail_mass_kg_per_m)
    B.rails("chassis", lo.nose_x, xf + lo.front_overhang, rail_z, lo.nose_half_width,
            2 * nose / 1000 * lo.rail_mass_kg_per_m, "nose rail")
    B.cross("chassis", "rear cross member", xr - lo.rear_overhang + (0 if hasattr(p, "kit") else 20), rail_z, hw)
    B.cross("chassis", "nose cross member", lo.nose_x, rail_z, hw)
    B.cross("chassis", "front cross member", xf + lo.front_overhang - 20, rail_z, lo.nose_half_width)

    # golf-cart front axle: beam + spindles + rack, on the frame
    fr = f.tire_diameter / 2
    for side in (1, -1):
        B.add("chassis", "wheel", f"front wheel {'L' if side > 0 else 'R'}", "cyl_y", (xf, side * f.track / 2, fr),
              (f.tire_diameter, f.tire_width), f.wheel_tire_mass_kg)
    beam_h = 2 * (fr - f.beam_clearance)
    B.add("chassis", "axle", "front beam axle", "box", (xf, 0, f.beam_clearance + beam_h / 2),
          (70, f.track - f.tire_width, beam_h), f.mass_kg)
    B.add("chassis", "steering", "steering rack", "cyl_y", (xf - 110, 0, f.beam_clearance + 30), (45, 520))
    tr.axles.append(Axle("front", xf, f.track, f.tire_diameter, f.tire_width, "chassis", False, f.beam_clearance,
                         f.tire_rim, f.tire_pressure_kpa))

    # power box: H0 slings it low between the rails under the seat, golf-cart style. Anywhere
    # above the rails it sits on a stand (e.g. over the front axle, where an engine would go).
    B.box_masses("chassis")
    L, W, H = box.outer
    bx, bz = lo.powerbox_x, lo.powerbox_z
    rail_top = rail_z + depth / 2
    if bz > rail_top + 5:
        B.add("chassis", "frame", "box stand", "box", (bx, 0, (rail_top + bz) / 2), (L - 40, W - 40, bz - rail_top),
              lo.box_stand_mass_kg)
    # operator station: the seat, floor, steering wheel and controls are placed from the operator
    oc = lo.operator_cg
    seat_z = lo.seat_height
    sx = oc[0] + 20
    on_box = abs(bx - sx) < L / 2 - 100 and abs(bz + H + 40 - seat_z) < 1
    if not on_box:            # a seat bridge: a post on each rail and a plate across, clear of what's below
        for side in (1, -1):
            B.add("chassis", "frame", f"seat post {'L' if side > 0 else 'R'}", "box",
                  (sx, side * hw, (rail_top + seat_z - 6) / 2), (300, 40, seat_z - 6 - rail_top), lo.seat_pedestal_mass_kg * 0.3)
        B.add("chassis", "frame", "seat pedestal", "box", (sx, 0, seat_z - 3), (300, 2 * hw + 40, 6),
              lo.seat_pedestal_mass_kg * 0.4)
    B.add("chassis", "seat", "seat pan", "box", (sx, 0, seat_z + 35), (420, 440, 70))
    B.add("chassis", "seat", "seat back", "box", (oc[0] - 190, 0, seat_z + 255), (60, 440, 420))
    B.add("chassis", "frame", "floor pan", "box", (oc[0] + lo.floor_reach, 0, rail_z + 45), (lo.floor_length, 2 * hw + 120, 10))
    controls = [oc[i] + lo.seat_and_controls_offset[i] for i in range(3)]
    # steering column: from the rack up and back to the wheel in front of the seat
    wheel = (oc[0] + lo.steering_wheel_reach, 0.0, lo.steering_wheel_height)
    if hasattr(p, "kit"):
        # Packaging hypothesis: longitudinal linkage below the battery, then
        # a column behind its enclosure. Actual linkage/effort needs design.
        elbow = (min(bx - L / 2 - 40, wheel[0]), 0.0, f.beam_clearance + 30)
        tr.links.append(Link("steering drag link", "seat", (xf - 110, 0, f.beam_clearance + 30), "chassis", elbow, "chassis", 24))
        tr.links.append(Link("steering column", "seat", elbow, "chassis", wheel, "chassis", 32))
    else:
        tr.links.append(Link("steering column", "seat", (xf - 110, 0, f.beam_clearance + 30), "chassis", wheel, "chassis", 32))
    B.add("chassis", "seat", "steering wheel", "cyl_z", wheel, (p.steering.steering_wheel_diameter, 25))
    B.add("chassis", "implement", "rear hitch", "box", (xr - lo.rear_overhang - 30, 0, rail_z - (110 if hasattr(p, "kit") else 60)), (60, 80, 40), lo.hitch_mass_kg)
    B.deck("chassis")                                           # mid-mount, between the axles
    B.mass("chassis", "seat & controls", lo.seat_and_controls_mass_kg, controls)
    B.mass("chassis", "operator", p.vehicle.mass_operator_kg, oc)
    if hasattr(p, "kit"):
        B.mass("chassis", "kit front body layer", p.kit.front_mass_kg,
               (bx, 0, bz + H / 2))
        B.mass("chassis", "kit rear body layer", p.kit.rear_mass_kg,
               (sx, 0, (rail_top + seat_z) / 2))
    if p.vehicle.mass_payload_kg:
        B.mass("chassis", "payload", p.vehicle.mass_payload_kg, controls)
    return tr


BUILDERS = {"articulated": build_pro, "steer_axle": build_home}


def build(p, box: powerbox.Layout | None = None) -> Tractor:
    """The machine, with its tyres' grip and rolling resistance worked out for
    its loads (eox.tyres.apply sets p.vehicle.traction_coefficient and
    rolling_resistance from each axle's tyre size, pressure and the ground)."""
    try:
        builder = BUILDERS[p.model.layout]
    except KeyError:
        raise NotImplementedError(f"layout '{p.model.layout}' has no builder yet") from None
    from eox import tyres
    tr = builder(p, box)
    tyres.apply(p, tr)
    return tr
