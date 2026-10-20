"""Drive a tractor over the test course in MuJoCo and score each obstacle.

The physics runs in MuJoCo (C); Python only steers at the control rate and
reads results. The driver holds the target speed (velocity-controlled drive
units, torque-limited at the motor's peak, through open diffs) and follows the
centreline with pure pursuit: Ackermann steering on the Home, the
articulation cylinder on the Pro (rate-limited to its lock-to-lock time).

Each obstacle is scored on its own. If the machine gets stuck, rolls over or
leaves the course, that obstacle fails and the machine is set down on the
flat past it, the way a test driver would be helped on, so every obstacle
gets a result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from eox.sim import mjcf, terrain

OUTCOMES = ("cleared", "stuck", "rolled over", "left the course", "not reached")


@dataclass
class Limits:
    wheel_lift_s: float
    peak_torque_s: float
    deck_float: float


@dataclass
class ObstacleResult:
    name: str
    kind: str
    rated: bool                      # False = beyond the model's rating: scored as information only
    limits: Limits
    outcome: str = "not reached"
    t_in: float = math.nan
    t_out: float = math.nan
    max_roll: float = 0.0            # deg, worst body
    max_pitch: float = 0.0
    min_wheel_n: float = math.inf    # lowest wheel load, averaged over 0.2 s (impacts make brief hops)
    min_wheel: str = ""
    lift_s: float = 0.0              # longest a wheel spent off the ground
    lift_wheel: str = ""
    peak_torque_x: float = 0.0       # motor torque / rated, worst drive unit
    at_peak_s: float = 0.0           # time a drive unit sat at its torque limit
    max_slip: float = 0.0            # driven wheels, %
    strikes: set = field(default_factory=set)
    deck_min_mm: float = math.inf    # deck underside to the ground, rigidly mounted (negative = it would dig in)
    joint_extremes: dict = field(default_factory=dict)
    snapshot: np.ndarray | None = None   # qpos at the obstacle's hardest moment (most roll + pitch)
    snapshot_t: float = math.nan
    _snap_score: float = -1.0

    @property
    def status(self) -> str:
        if not self.rated:
            return "INFO"
        if self.outcome != "cleared":
            return "FAIL"
        return "WARN" if self.warnings else "PASS"

    @property
    def warnings(self) -> list[str]:
        w, lim = [], self.limits
        if self.lift_s >= lim.wheel_lift_s:
            w.append(f"{self.lift_wheel.replace('_', ' ')} wheel lifts {self.lift_s:.1f} s")
        if self.strikes:
            w.append("strikes: " + ", ".join(sorted(s.split(":", 1)[1] for s in self.strikes)))
        if self.deck_min_mm < -lim.deck_float:
            w.append(f"deck needs {-self.deck_min_mm:.0f} mm of float (has {lim.deck_float:g})")
        if self.at_peak_s > lim.peak_torque_s:
            w.append(f"motor at peak torque {self.at_peak_s:.1f} s")
        return w


@dataclass
class RunResult:
    model: str
    config: str
    obstacles: list[ObstacleResult]
    completed: bool
    time_s: float
    energy_wh: float                 # drive energy at the wheels
    recoveries: int
    times: np.ndarray = None
    qpos: np.ndarray = None          # trajectory at the control rate, for playback


def yaw_roll_pitch(xmat) -> tuple[float, float, float]:
    R = np.asarray(xmat).reshape(3, 3)
    yaw = math.atan2(R[1, 0], R[0, 0])
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -R[2, 0]))))
    roll = math.degrees(math.atan2(R[2, 1], R[2, 2]))
    return yaw, roll, pitch


class Driver:
    """The test driver: pure pursuit on the centreline (y = 0); speed held by
    the drive units' velocity loop plus integral action, so the machine
    doesn't droop on a climb. When the tyres lose grip the wheels spin."""

    KI = 2.0                      # 1/s, speed integral

    def __init__(self, spec: mjcf.Spec, speed_ms: float, lookahead: float):
        self.s, self.v, self.ld = spec, speed_ms, lookahead
        self.restart(0.0)

    def restart(self, t: float):
        self.gamma, self.t_go = 0.0, t
        self.integral = {nm: 0.0 for nm in self.s.drives}

    def __call__(self, d, t: float, dt: float, v_ground: float = 0.0):
        s = self.s
        ramp = min(1.0, max(0.0, (t - self.t_go) / 2.0))           # ease off the line
        for nm, dr in s.drives.items():
            r = next(w.radius for w in s.wheels if w.axle == dr["axle"])
            want = self.v * ramp / r                                # rad/s at the wheel
            spin = float(d.actuator(nm).velocity[0]) / 2            # mean wheel speed (open diff)
            self.integral[nm] = min(max(self.integral[nm] + self.KI * (want - spin) * dt, 0.0), 0.5 * want + 1.0)
            d.actuator(nm).ctrl[0] = 2 * (want + self.integral[nm])
        rear = [d.body(w.name).xpos for w in s.wheels if w.axle == "rear"]
        px, py = (rear[0][0] + rear[1][0]) / 2, (rear[0][1] + rear[1][1]) / 2
        yaw, _, _ = yaw_roll_pitch(d.body(s.root).xmat)
        alpha = math.atan2(-py, self.ld) - yaw
        kappa = 2 * math.sin(alpha) / self.ld
        st = s.steer
        if st["kind"] == "ackermann":
            L, t2 = st["wheelbase"], st["track"] / 2
            delta = max(-st["max"], min(st["max"], math.atan(kappa * L)))
            if abs(delta) < 1e-4:
                dl = dr_ = delta
            else:
                R = L / math.tan(delta)
                dl, dr_ = math.atan(L / (R - t2)), math.atan(L / (R + t2))
            d.actuator(st["actuators"][0]).ctrl[0] = dl
            d.actuator(st["actuators"][1]).ctrl[0] = dr_
        else:
            want = max(-st["max"], min(st["max"], kappa * (st["a"] + st["b"])))
            step = st["rate"] * dt
            self.gamma += max(-step, min(step, want - self.gamma))
            d.actuator(st["actuator"]).ctrl[0] = self.gamma


class _Rig:
    """The compiled model plus the lookups the scorer needs every step."""

    def __init__(self, spec, m, course):
        import mujoco
        self.spec, self.m, self.course = spec, m, course
        gid = {mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i): i for i in range(m.ngeom)}
        self.terrain = gid["terrain"]
        self.tyre_of = {gid[f"{w.name}:tyre"]: w for w in spec.wheels}
        self.deck = gid.get(spec.deck_geom) if spec.deck_geom else None
        self.halves = [m.body(h).id for h in spec.halves]
        self.spin_dof = {w.name: m.jnt_dofadr[m.joint(f"{w.name}:spin").id] for w in spec.wheels}
        self.parent = {w.name: m.body_parentid[m.body(w.name).id] for w in spec.wheels}
        self.f6 = np.zeros(6)

    def wheel_loads(self, d) -> tuple[dict, set]:
        import mujoco
        loads = {w.name: 0.0 for w in self.spec.wheels}
        strikes = set()
        for i in range(d.ncon):
            con = d.contact[i]
            g1, g2 = con.geom1, con.geom2
            other = g2 if g1 == self.terrain else g1 if g2 == self.terrain else None
            if other is None:
                continue
            if other in self.tyre_of:
                mujoco.mj_contactForce(self.m, d, i, self.f6)
                loads[self.tyre_of[other].name] += self.f6[0]
            else:
                strikes.add(self.m.geom(other).name)
        return loads, strikes

    def rolling_resistance(self, d, loads):
        """Turf motion resistance as a force at each wheel centre, against its
        rolling direction. As a ground force it uses up the driven tyres' grip
        (net traction = gross - resistance), the way the drive calc counts it."""
        crr = self.spec.rolling_resistance
        for w in self.spec.wheels:
            b = self.m.body(w.name).id
            fwd = d.xmat[self.parent[w.name]].reshape(3, 3)[:, 0]
            v = float(_point_velocity(self.m, d, w.name) @ fwd)
            d.xfrc_applied[b, :3] = -crr * loads[w.name] * math.tanh(v / 0.1) * fwd

    def drive_state(self, d, dt):
        """Worst motor torque (x rated), whether a unit is at its limit, worst slip %, wheel energy."""
        peak_x, saturated, slip, energy = 0.0, False, 0.0, 0.0
        for nm, dr in self.spec.drives.items():
            f = float(d.actuator(nm).force[0])                       # N*m at each wheel (open diff)
            peak_x = max(peak_x, abs(2 * f) / (dr["ratio"] * dr["eta"]) / dr["T_rated"])
            saturated |= abs(f) >= 0.98 * dr["wheel_torque_max"]
            for w in self.spec.wheels:
                if w.axle != dr["axle"]:
                    continue
                omega = float(d.qvel[self.spin_dof[w.name]])
                fwd = d.xmat[self.parent[w.name]].reshape(3, 3)[:, 0]
                v_fwd = float(_point_velocity(self.m, d, w.name) @ fwd)
                rim = omega * w.radius
                if max(abs(rim), abs(v_fwd)) > 0.15:
                    slip = max(slip, abs(rim - v_fwd) / max(abs(rim), abs(v_fwd)) * 100)
                energy += abs(f * omega) * dt / 3600
        return peak_x, saturated, slip, energy

    def ground_speed(self, d) -> float:
        fwd = d.xmat[self.m.body(self.spec.root).id].reshape(3, 3)[:, 0]
        return float(_point_velocity(self.m, d, self.spec.root) @ fwd)

    def deck_clearance(self, d) -> float:
        if self.deck is None:
            return math.inf
        gx, gm, sz = d.geom_xpos[self.deck], d.geom_xmat[self.deck].reshape(3, 3), self.m.geom_size[self.deck]
        low = math.inf
        for ix in (-1, -0.5, 0, 0.5, 1):
            for iy in (-1, -0.5, 0, 0.5, 1):
                pt = gx + gm @ np.array([ix * sz[0], iy * sz[1], -sz[2]])
                low = min(low, (pt[2] - self.course.height(pt[0], pt[1])) * 1000)
        return low


def _point_velocity(m, d, body: str) -> np.ndarray:
    import mujoco
    vel = np.zeros(6)
    mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, m.body(body).id, vel, 0)
    return vel[3:]


def _set_down(m, d, spec, course, x_rear: float, settle_s: float):
    """Put the machine back on the flat with its rear axle at x_rear, wheels straight."""
    import mujoco
    mujoco.mj_resetData(m, d)
    d.qpos[0] = x_rear + (spec.start[0] - spec.start_rear_x)
    d.qpos[2] = course.height(x_rear, 0) + 0.01
    mujoco.mj_forward(m, d)
    mujoco.mj_step(m, d, nstep=int(settle_s / m.opt.timestep))


def run(p, tr, fitted: tuple = (), config: str | None = None, keep_trajectory: bool = True) -> RunResult:
    import mujoco

    c = p.course
    sim, sc = c.sim, c.scoring
    lim = Limits(sc.wheel_lift_s, sc.peak_torque_s, sc.deck_float)
    course = terrain.build(c)
    spec = mjcf.build(p, tr, course, fitted)
    spec.start_rear_x = c.start_x
    m = mjcf.load(spec)
    d = mujoco.MjData(m)
    rig = _Rig(spec, m, course)
    config = config or ("deck fitted" if fitted else "bare")
    v = c.speed_kmh / 3.6
    drv = Driver(spec, v, lookahead=max(2.0, 1.5 * spec.wheelbase))
    n_sub = max(1, int(round(1.0 / (sim.control_hz * sim.timestep))))
    dt = n_sub * sim.timestep

    veh = p.vehicle
    beyond = {"ramp": veh.max_slope_deg, "side_slope": getattr(veh, "max_cross_slope_deg", veh.max_slope_deg)}
    obs = [ObstacleResult(s.name, s.kind, not (s.kind in beyond and s.spec.slope_deg > beyond[s.kind]), lim)
           for s in course.segments]
    r_max = max(w.radius for w in spec.wheels)

    mujoco.mj_step(m, d, nstep=int(sim.settle_s / sim.timestep))
    t = 0.0
    end_x = course.length - c.run_out / 2
    t_limit = sim.time_limit_factor * course.length / v
    last_progress_t, best_x = 0.0, -1e9
    lift_run = {w.name: 0.0 for w in spec.wheels}
    smooth = {w.name: 0.0 for w in spec.wheels}
    k_s = dt / 0.2
    energy, recoveries = 0.0, 0
    times, traj = [], []
    completed = False
    loads = {w.name: 0.0 for w in spec.wheels}

    while t < t_limit:
        rig.rolling_resistance(d, loads)
        drv(d, t, dt, rig.ground_speed(d))
        mujoco.mj_step(m, d, nstep=n_sub)
        t += dt

        wx = [d.body(w.name).xpos for w in spec.wheels]
        x_lo, x_hi = min(q[0] for q in wx) - r_max, max(q[0] for q in wx) + r_max
        x_mid = (x_lo + x_hi) / 2
        y_mid = float(np.mean([q[1] for q in wx]))
        if keep_trajectory:
            times.append(t)
            traj.append(d.qpos.copy())

        loads, strikes = rig.wheel_loads(d)
        angles = [yaw_roll_pitch(d.xmat[b])[1:] for b in rig.halves]
        roll = max(abs(a[0]) for a in angles)
        pitch = max(abs(a[1]) for a in angles)
        peak_x, saturated, slip, e = rig.drive_state(d, dt)
        energy += e
        deck_clear = rig.deck_clearance(d)
        for w in spec.wheels:
            lift_run[w.name] = lift_run[w.name] + dt if loads[w.name] < sc.wheel_lift_n else 0.0
            smooth[w.name] += k_s * (loads[w.name] - smooth[w.name])

        current = None
        for seg, ob in zip(course.segments, obs):
            if not (x_hi >= seg.x0 and x_lo <= seg.x1):
                if ob.outcome == "not reached" and x_lo > seg.x1:
                    ob.outcome = "cleared"
                continue
            current = (seg, ob)
            if math.isnan(ob.t_in):
                ob.t_in = t
            ob.t_out = t
            ob.max_roll, ob.max_pitch = max(ob.max_roll, roll), max(ob.max_pitch, pitch)
            for w in spec.wheels:
                if smooth[w.name] < ob.min_wheel_n:
                    ob.min_wheel_n, ob.min_wheel = smooth[w.name], w.name
                if lift_run[w.name] > ob.lift_s:
                    ob.lift_s, ob.lift_wheel = lift_run[w.name], w.name
            ob.peak_torque_x = max(ob.peak_torque_x, peak_x)
            ob.at_peak_s += dt if saturated else 0.0
            ob.max_slip = max(ob.max_slip, slip)
            ob.strikes |= strikes
            ob.deck_min_mm = min(ob.deck_min_mm, deck_clear)
            for role, jn in spec.joints.items():
                q = float(d.joint(jn).qpos[0])
                q = q * 1000 if role == "bounce" else math.degrees(q)
                ob.joint_extremes[role] = max(ob.joint_extremes.get(role, 0.0), abs(q))
            score = roll + pitch + 0.2 * sum(ob.joint_extremes.values())
            if score > ob._snap_score and x_lo > seg.x0 - 0.5:
                ob.snapshot, ob.snapshot_t, ob._snap_score = d.qpos.copy(), t, score

        if x_mid > best_x + 0.05:
            best_x, last_progress_t = x_mid, t
        reason = None
        if roll > sim.rolled_deg or pitch > sim.rolled_deg:
            reason = "rolled over"
        elif abs(y_mid) > sc.lateral_limit:
            reason = "left the course"
        elif t - last_progress_t > sim.stuck_s:
            reason = "stuck"
        if reason:
            seg, ob = current if current else min(
                ((s, o) for s, o in zip(course.segments, obs) if s.x1 >= x_lo), key=lambda so: so[0].x0)
            ob.outcome = reason
            if ob.snapshot is None:
                ob.snapshot, ob.snapshot_t = d.qpos.copy(), t
            recoveries += 1
            _set_down(m, d, spec, course, seg.x1 + 0.3 + r_max, 1.0)
            drv.restart(t)
            last_progress_t, best_x = t, -1e9
            lift_run = dict.fromkeys(lift_run, 0.0)
            smooth = {w.name: 0.0 for w in spec.wheels}
            loads = dict.fromkeys(loads, 0.0)
            continue
        if x_lo > end_x:
            completed = True
            break
    else:                                    # out of time: whatever it's on, it was crawling, not getting over
        if current:
            current[1].outcome = "stuck"

    return RunResult(spec.model_name, config, obs, completed, t, energy, recoveries,
                     np.asarray(times), np.asarray(traj))
