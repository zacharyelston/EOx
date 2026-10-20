"""Generate a MuJoCo model (MJCF) of a tractor on the test course.

Built from the same Tractor object the calcs and CAD use, so the simulated
machine carries exactly the reconciled masses (tests/test_mass.py) and the
same part envelopes:

  Home  chassis (free) -> leaf-sprung front beam axle (bounce + roll springs)
        -> two steering knuckles (kingpins) -> front wheels; rear wheels on
        the chassis, driven through an open diff.
  Pro   rear half (free) -> knuckle on the roll trunnion (+-oscillation)
        -> front half on the yaw pins, steered by the cylinder; both axles
        driven through open diffs.

Tyres are ellipsoids with sliding + torsional friction (condim 4); rolling
resistance is applied as a force at each wheel centre (sim.run), because
MuJoCo's contact rolling friction makes heightfield contacts chatter. Every other part envelope
collides with the ground (strikes are scored). The deck
and its PTO unit are drawn but don't collide: a real deck rides on anti-scalp
rollers, so ground contact under the deck is scored as scalping instead.
Units: metres, kilograms, seconds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from eox.powerbox import Body
from eox.tractor import Tractor

MM = 1e-3
G = 9.81

RGBA = {
    "wheel": "0.07 0.07 0.07 1", "hub": "0.55 0.56 0.58 1", "axle": "0.30 0.30 0.32 1",
    "motor": "0.15 0.22 0.30 1", "controller": "0.04 0.04 0.04 1", "frame": "0.62 0.15 0.12 1",
    "pivot": "0.80 0.65 0.10 1", "steering": "0.80 0.65 0.10 1", "implement": "0.62 0.15 0.12 1",
    "seat": "0.12 0.12 0.12 1", "powerbox": "0.80 0.82 0.84 1", "deck": "0.45 0.11 0.09 1",
    "pto": "0.15 0.22 0.30 1",
}
VISUAL_ONLY = {"deck", "pto"}


@dataclass
class Wheel:
    name: str            # body name; the geom is "<name>:tyre", the joint "<name>:spin"
    axle: str            # "front" | "rear"
    side: int            # +1 left, -1 right
    radius: float
    driven: bool


@dataclass
class Spec:
    """What the runner needs to know about the generated model."""
    model_name: str
    root: str
    halves: list[str]                    # bodies whose roll / pitch is tracked
    wheels: list[Wheel]
    drives: dict[str, dict]              # actuator -> axle, wheel torque limit, overall ratio, efficiency
    steer: dict                          # how the machine steers (kind, actuators, geometry, limits)
    deck_geom: str | None
    start: tuple[float, float, float]    # world position of the tractor origin at the start
    wheelbase: float
    xml: str = ""
    joints: dict[str, str] = field(default_factory=dict)   # role -> joint name (suspension, trunnion...)


# ---------------------------------------------------------------------------
# mass properties
# ---------------------------------------------------------------------------
def _box_inertia(m, dx, dy, dz):
    return np.diag([m * (dy * dy + dz * dz) / 12, m * (dx * dx + dz * dz) / 12, m * (dx * dx + dy * dy) / 12])


class _Inertia:
    def __init__(self):
        self.items = []                  # (kg, centre (m, world-at-rest), 3x3 about own centre)

    def add(self, kg, c, dims=None):
        I = _box_inertia(kg, *dims) if dims is not None else np.zeros((3, 3))
        self.items.append((kg, np.asarray(c, float), I))

    def xml(self, origin) -> str:
        M = sum(k for k, _, _ in self.items)
        c = sum(k * p for k, p, _ in self.items) / M
        I = np.zeros((3, 3))
        for k, p, Ii in self.items:
            d = p - c
            I += Ii + k * (d @ d * np.eye(3) - np.outer(d, d))
        I += np.eye(3) * 1e-4
        o = np.asarray(origin, float)
        full = f"{I[0,0]:.5g} {I[1,1]:.5g} {I[2,2]:.5g} {I[0,1]:.5g} {I[0,2]:.5g} {I[1,2]:.5g}"
        return f'<inertial pos="{_v(c - o)}" mass="{M:.4g}" fullinertia="{full}"/>'

    @property
    def mass(self):
        return sum(k for k, _, _ in self.items)


def _v(a) -> str:
    return " ".join(f"{x:.5g}" for x in a)


def _dims(b: Body):
    x0, x1, y0, y1, z0, z1 = b.bounds()
    return ((x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM)


def _geom(name, b: Body, origin, kind, collide=True) -> str:
    c = np.asarray(b.center) * MM - np.asarray(origin)
    cls = "" if collide else ' class="visual"'
    rgba = RGBA.get(kind, "0.6 0.6 0.6 1")
    if b.shape == "box":
        hx, hy, hz = (s * MM / 2 for s in b.size)
        return f'<geom name="{name}" type="box" size="{hx:.4g} {hy:.4g} {hz:.4g}" pos="{_v(c)}" rgba="{rgba}"{cls}/>'
    r, h = b.size[0] * MM / 2, b.size[1] * MM / 2
    euler = {"cyl_x": "0 1.5708 0", "cyl_y": "1.5708 0 0", "cyl_z": "0 0 0"}[b.shape]
    return (f'<geom name="{name}" type="cylinder" size="{r:.4g} {h:.4g}" pos="{_v(c)}" euler="{euler}" '
            f'rgba="{rgba}"{cls}/>')


def _look(pos, target=(0, 0, 0.5)) -> str:
    """Camera xyaxes looking from pos at target."""
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    x = np.cross(f, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(x, f)
    return f"{_v(x)} {_v(y)}"


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------
def build(p, tr: Tractor, course, fitted: tuple = ()) -> Spec:
    c, u, a = p.course, p.unit, p.axle
    sim = c.sim
    mu, crr = p.vehicle.traction_coefficient, p.vehicle.rolling_resistance
    rear = tr.axle("rear")
    start = (c.start_x - rear.x * MM, 0.0, 0.0)

    # which MuJoCo body each tractor group / part belongs to
    if tr.articulated:
        root, halves = "rear", ["rear", "front"]
        body_of_group = {"rear": "rear", "front": "front"}
        special = {("rear", "knuckle"): "knuckle", ("rear", "knuckle steering arm"): "knuckle"}
        origins = {"rear": (0, 0, 0), "knuckle": (0, 0, 0), "front": (0, 0, 0)}
    else:
        f = p.steer_axle
        root, halves = "chassis", ["chassis"]
        body_of_group = {"chassis": "chassis"}
        special = {("chassis", "front beam axle"): "front_axle", ("chassis", "steering rack"): "front_axle"}
        origins = {"chassis": (0, 0, 0), "front_axle": (tr.axle("front").x * MM, 0, f.tire_diameter / 2 * MM)}
    inert = {b: _Inertia() for b in origins}
    geoms = {b: [] for b in origins}

    # part envelopes -> geoms; masses that belong to a part get its box inertia
    wheel_parts = set()
    dims_by_part = {}
    seen = {}
    for group, kind, b in tr.bodies:
        dims_by_part[(group, b.name, tuple(b.center))] = _dims(b)
        if kind == "wheel":
            wheel_parts.add((group, b.name))
            continue
        if kind in VISUAL_ONLY and "deck" not in fitted:
            continue
        mjb = special.get((group, b.name), body_of_group[group])
        name = f"{group}:{b.name}"
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            name += f" {seen[name]}"
        geoms[mjb].append(_geom(name, b, origins[mjb], kind, collide=kind not in VISUAL_ONLY))
    L, W, H = tr.box.outer
    bx, _, bz = tr.box_pos
    box = Body("power box", "box", (bx, 0, bz + H / 2), (L, W, H))
    gb = body_of_group[tr.box_group]
    geoms[gb].append(_geom(f"{tr.box_group}:power box", box, origins[gb], "powerbox"))
    box_dims = {f"box {b.name}": _dims(b) for b in tr.box.bodies}

    wheel_mass = {}
    for m in tr._counted(None, fitted):
        if (m.group, m.name) in wheel_parts:
            wheel_mass[(m.group, m.name)] = m.kg
            continue
        mjb = special.get((m.group, m.name), body_of_group.get(m.group))
        dims = dims_by_part.get((m.group, m.name, tuple(m.cg))) or box_dims.get(m.name)
        if m.name == "operator":
            dims = (0.45, 0.45, 0.90)
        inert[mjb].add(m.kg, np.asarray(m.cg) * MM, dims)

    # wheels
    wheels: list[Wheel] = []

    def wheel_xml(name, axle, side, pos, r, w, kg, driven):
        wheels.append(Wheel(name, axle, side, r, driven))
        Ir = kg * (3 * r * r + w * w) / 12
        return (f'<body name="{name}" pos="{_v(pos)}">'
                f'<joint name="{name}:spin" type="hinge" axis="0 1 0" damping="0.5"/>'
                f'<inertial pos="0 0 0" mass="{kg:.4g}" diaginertia="{Ir:.4g} {0.6 * kg * r * r:.4g} {Ir:.4g}"/>'
                f'<geom name="{name}:tyre" class="tyre" type="ellipsoid" size="{r:.4g} {w / 2:.4g} {r:.4g}"/>'
                f'<geom class="visual" type="cylinder" size="{r * 0.995:.4g} {w / 2:.4g}" euler="1.5708 0 0" rgba="{RGBA["wheel"]}"/>'
                f'<geom class="visual" type="cylinder" size="{r * 0.45:.4g} {w / 2 + 0.002:.4g}" euler="1.5708 0 0" rgba="{RGBA["hub"]}"/>'
                f'<geom class="visual" type="box" size="{r * 0.9:.4g} {w / 2 + 0.004:.4g} 0.02" rgba="{RGBA["hub"]}"/>'
                f'</body>')

    def drive_wheels(group, ax, origin):
        r, w = ax.tire_diameter / 2 * MM, ax.tire_width * MM
        out = []
        for side, nm in ((1, "wheel L"), (-1, "wheel R")):
            pos = np.array([ax.x * MM, side * ax.track / 2 * MM, r]) - np.asarray(origin)
            out.append(wheel_xml(f"{ax.name}_{'L' if side > 0 else 'R'}", ax.name, side, pos, r, w,
                                 wheel_mass[(group, nm)], ax.driven))
        return "".join(out)

    T_rated = u.rated_power_w / (2 * math.pi * u.base_speed_rpm / 60)
    T_peak = T_rated * u.peak_torque_factor
    ratio, eta = a.ratio * a.extra_reduction, a.efficiency
    per_wheel = T_peak * ratio * eta / 2                 # open diff: equal torque each side
    drives = {}
    tendons, actuators = [], []
    for ax in tr.axles:
        if not ax.driven:
            continue
        nm = f"drive_{ax.name}"
        drives[nm] = dict(axle=ax.name, wheel_torque_max=per_wheel, ratio=ratio, eta=eta, T_rated=T_rated, T_peak=T_peak)
        tendons.append(f'<fixed name="{nm}"><joint joint="{ax.name}_L:spin" coef="1"/><joint joint="{ax.name}_R:spin" coef="1"/></fixed>')
        r = ax.tire_diameter / 2 * MM
        vmax = 2 * 12 / 3.6 / r
        actuators.append(f'<velocity name="{nm}" tendon="{nm}" kv="{sim.drive_gain:g}" ctrlrange="{-vmax:.3g} {vmax:.3g}" '
                         f'forcerange="{-per_wheel:.4g} {per_wheel:.4g}"/>')

    joints = {}
    if tr.articulated:
        lo, st = p.layout, p.steering
        ph = lo.pivot_height * MM
        gmax = math.radians(lo.articulation_max_deg)
        ra = math.radians(lo.oscillation_max_deg)
        A_rod = math.pi / 4 * (st.bore ** 2 - st.rod ** 2)
        M_cyl = st.relief_bar * 0.1 * A_rod * st.lever_arm / 1000 * math.cos(gmax)   # N*m at full lock, as the calc
        body_xml = (
            f'<body name="rear" pos="{_v(start)}"><freejoint name="root"/>{inert["rear"].xml(origins["rear"])}'
            + "".join(geoms["rear"]) + drive_wheels("rear", tr.axle("rear"), origins["rear"])
            + f'<camera name="chase" mode="trackcom" pos="-2.3 -3.4 1.7" xyaxes="{_look((-2.3, -3.4, 1.7), (0.3, 0, 0))}"/>'
            + f'<camera name="side" mode="trackcom" pos="0.2 -5.5 0.9" xyaxes="{_look((0.2, -5.5, 0.9), (0.2, 0, 0.3))}"/>'
            + f'<camera name="front" mode="trackcom" pos="4.5 -2.5 1.6" xyaxes="{_look((4.5, -2.5, 1.6), (0, 0, 0.2))}"/>'
            + f'<body name="knuckle" pos="0 0 0">'
            f'<joint name="trunnion" type="hinge" axis="1 0 0" pos="0 0 {ph:.4g}" range="{-ra:.4g} {ra:.4g}" damping="150"/>'
            + inert["knuckle"].xml(origins["knuckle"]) + "".join(geoms["knuckle"])
            + f'<body name="front" pos="0 0 0">'
            f'<joint name="yaw" type="hinge" axis="0 0 1" pos="0 0 {ph:.4g}" range="{-gmax - 0.02:.4g} {gmax + 0.02:.4g}" damping="400"/>'
            + inert["front"].xml(origins["front"]) + "".join(geoms["front"])
            + drive_wheels("front", tr.axle("front"), origins["front"])
            + "</body></body></body>")
        actuators.append(f'<position name="steer" joint="yaw" kp="30000" kv="3000" ctrlrange="{-gmax:.4g} {gmax:.4g}" '
                         f'forcerange="{-M_cyl:.5g} {M_cyl:.5g}"/>')
        steer = dict(kind="articulated", actuator="steer", joint="yaw", max=gmax,
                     rate=2 * gmax / max(_lock_to_lock_s(st, gmax), 0.5), torque=M_cyl,
                     a=lo.front_axle_x * MM, b=-lo.rear_axle_x * MM)
        joints = {"trunnion": "trunnion", "yaw": "yaw"}
        wheelbase = (lo.front_axle_x - lo.rear_axle_x) * MM
    else:
        f = p.steer_axle
        fa = tr.axle("front")
        r, w, t = f.tire_diameter / 2 * MM, f.tire_width * MM, f.track * MM
        k = f.spring_rate_n_per_mm * 1000                # N/m per spring
        s = f.spring_spacing * MM
        trav = f.spring_travel * MM
        k_bounce, k_roll = 2 * k, k * s * s / 2
        unsprung = inert["front_axle"].mass + 2 * f.wheel_tire_mass_kg
        sprung_load = tr.axle_loads_n(fitted=fitted)["front"] - unsprung * G
        mmax = math.radians(f.max_steer_deg)
        knuckles = "".join(
            f'<body name="kingpin_{sd}" pos="0 {side * t / 2:.4g} 0">'
            f'<joint name="steer_{sd}" type="hinge" axis="0 0 1" range="{-mmax:.4g} {mmax:.4g}" damping="30"/>'
            f'<inertial pos="0 0 0" mass="0.01" diaginertia="1e-4 1e-4 1e-4"/>'
            + wheel_xml(f"front_{sd}", "front", side, (0, 0, 0), r, w, wheel_mass[("chassis", f"front wheel {sd}")], False)
            + "</body>" for side, sd in ((1, "L"), (-1, "R")))
        body_xml = (
            f'<body name="chassis" pos="{_v(start)}"><freejoint name="root"/>{inert["chassis"].xml(origins["chassis"])}'
            + "".join(geoms["chassis"]) + drive_wheels("chassis", rear, origins["chassis"])
            + (f'<geom class="visual" type="capsule" size="0.016" fromto="{_v(np.asarray(tr.links[0].a) * MM)} '
               f'{_v(np.asarray(tr.links[0].b) * MM)}" rgba="{RGBA["steering"]}"/>' if tr.links else "")
            + f'<camera name="chase" mode="trackcom" pos="-2.2 -3.4 1.7" xyaxes="{_look((-2.2, -3.4, 1.7), (0.3, 0, 0))}"/>'
            + f'<camera name="side" mode="trackcom" pos="0.2 -5.5 0.9" xyaxes="{_look((0.2, -5.5, 0.9), (0.2, 0, 0.3))}"/>'
            + f'<camera name="front" mode="trackcom" pos="4.5 -2.5 1.6" xyaxes="{_look((4.5, -2.5, 1.6), (0, 0, 0.2))}"/>'
            + f'<body name="front_axle" pos="{_v(origins["front_axle"])}">'
            f'<joint name="bounce" type="slide" axis="0 0 1" range="{-trav:.4g} {trav:.4g}" stiffness="{k_bounce:.5g}" '
            f'springref="{-sprung_load / k_bounce:.5g}" damping="{0.3 * 2 * math.sqrt(k_bounce * 60):.4g}"/>'
            f'<joint name="axle_roll" type="hinge" axis="1 0 0" range="{-math.atan(2 * trav / s):.4g} {math.atan(2 * trav / s):.4g}" '
            f'stiffness="{k_roll:.5g}" damping="{0.3 * 2 * math.sqrt(k_roll * 3):.4g}"/>'
            + inert["front_axle"].xml(origins["front_axle"]) + "".join(geoms["front_axle"]) + knuckles
            + "</body></body>")
        for sd in ("L", "R"):
            actuators.append(f'<position name="steer_{sd}" joint="steer_{sd}" kp="4000" kv="150" '
                             f'ctrlrange="{-mmax:.4g} {mmax:.4g}" forcerange="-1500 1500"/>')
        steer = dict(kind="ackermann", actuators=("steer_L", "steer_R"), max=mmax, track=t,
                     wheelbase=(fa.x - rear.x) * MM)
        joints = {"bounce": "bounce", "axle_roll": "axle_roll"}
        wheelbase = (fa.x - rear.x) * MM

    # terrain
    zmin, zmax = float(course.z.min()), float(course.z.max())
    elev = max(zmax - zmin, 1e-3)
    rx, ry = course.length / 2, course.width / 2
    friction = f"{mu:g} {sim.friction_torsional:g} 0"     # rolling resistance is a wheel-centre force (sim.run)
    xml = f"""<mujoco model="{p.model.name} on the {course.name}">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{sim.timestep}" integrator="implicitfast" cone="elliptic" impratio="10"/>
  <size memory="64M"/>
  <visual>
    <global offwidth="1920" offheight="1080" azimuth="-130" elevation="-20"/>
    <quality shadowsize="4096" offsamples="8"/>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.45 0.45 0.45" specular="0.1 0.1 0.1"/>
    <map znear="0.02" zfar="200"/>
  </visual>
  <default>
    <geom contype="0" conaffinity="1" condim="3" friction="{friction}"/>
    <default class="tyre"><geom condim="4" rgba="0.07 0.07 0.07 0" group="3"/></default>
    <default class="visual"><geom contype="0" conaffinity="0" group="1" mass="0"/></default>
  </default>
  <asset>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.70 0.82 0.95" rgb2="0.97 0.98 1" width="512" height="512"/>
    <texture name="grass" type="2d" builtin="checker" rgb1="0.40 0.58 0.28" rgb2="0.36 0.53 0.25" width="512" height="512" mark="edge" markrgb="0.30 0.44 0.21"/>
    <material name="grass" texture="grass" texrepeat="1 1" texuniform="true" reflectance="0"/>
    <hfield name="course" nrow="{len(course.ys)}" ncol="{len(course.xs)}" size="{rx:.4g} {ry:.4g} {elev:.4g} 0.5"/>
  </asset>
  <worldbody>
    <light name="sun" directional="true" pos="0 0 10" dir="-0.4 0.3 -1" diffuse="0.75 0.75 0.72" castshadow="true"/>
    <geom name="terrain" type="hfield" hfield="course" pos="{rx:.4g} 0 {zmin:.4g}" material="grass" contype="1" conaffinity="0"/>
    {body_xml}
  </worldbody>
  <tendon>{''.join(tendons)}</tendon>
  <actuator>{''.join(actuators)}</actuator>
</mujoco>
"""
    deck_group = next((g for g, k, _ in tr.bodies if k == "deck"), None)
    deck = f"{deck_group}:mower deck" if "deck" in fitted and deck_group else None
    spec = Spec(p.model.name, root, halves, wheels, drives, steer, deck, start, wheelbase, xml, joints)
    spec.hfield = ((course.z - zmin) / elev).astype(np.float32).ravel()
    spec.rolling_resistance = crr
    return spec


def _lock_to_lock_s(st, gmax) -> float:
    A_full = math.pi / 4 * st.bore ** 2
    A_rod = math.pi / 4 * (st.bore ** 2 - st.rod ** 2)
    stroke = 2 * st.lever_arm * math.sin(gmax)
    return stroke * (A_full + A_rod) / 2 / (st.pump_flow_lpm * 1e6 / 60)


def export(spec: Spec, xml_path) -> None:
    """Write the model for MuJoCo's own viewer (`simulate`): the MJCF plus the
    heightfield as MuJoCo's binary format (int32 nrow, int32 ncol, float32 data)."""
    from pathlib import Path
    xml_path = Path(xml_path)
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    bin_path = xml_path.with_suffix(".hfield.bin")
    import re
    nrow, ncol = (int(v) for v in re.search(r'<hfield name="course" nrow="(\d+)" ncol="(\d+)"', spec.xml).groups())
    with open(bin_path, "wb") as f:
        np.array([nrow, ncol], np.int32).tofile(f)
        spec.hfield.astype(np.float32).tofile(f)
    xml_path.write_text(spec.xml.replace('<hfield name="course" nrow="{0}" ncol="{1}"'.format(nrow, ncol),
                                         f'<hfield name="course" file="{bin_path.name}"'))


def load(spec: Spec):
    """Compile the MJCF and fill the heightfield."""
    import mujoco
    m = mujoco.MjModel.from_xml_string(spec.xml)
    m.hfield_data[:] = spec.hfield
    return m
