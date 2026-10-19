"""Terrain course in MuJoCo (src/eox/sim): the course geometry, the generated
model against the calcs, and regression runs for both models with the deck."""
import math
import types

import mujoco
import numpy as np
import pytest

from eox import tractor
from eox.params import load
from eox.sim import mjcf, report, terrain
from eox.sim import run as sim
from eox.tractor import DECK

CONFIGS = [((), "bare"), (DECK, "deck")]


def _flat(p):
    p.course.obstacle = []
    p.course.run_in = 10.0
    return p


def test_course_follows_its_definition():
    c = terrain.build(load("home").course)
    assert [s.name for s in c.segments] == [ob.name for ob in load("home").course.obstacle]
    assert all(a.x1 < b.x0 for a, b in zip(c.segments, c.segments[1:]))      # flat gaps between obstacles
    xs, zc = c.centreline()
    for s in c.segments:
        m = (xs >= s.x0) & (xs <= s.x1)
        if s.kind == "ramp":
            grade = np.degrees(np.arctan(np.gradient(zc, c.res)[m]))
            assert grade.max() == pytest.approx(s.spec.slope_deg, abs=0.3)
            assert zc[m].max() == pytest.approx(s.spec.rise, abs=0.01)
        if s.kind == "side_slope":
            xm = (s.x0 + s.x1) / 2
            tilt = math.degrees(math.atan((c.height(xm, 1.0) - c.height(xm, -1.0)) / 2))
            assert tilt == pytest.approx(s.spec.slope_deg, abs=0.1)


@pytest.mark.parametrize("model", ["home", "pro"])
@pytest.mark.parametrize("fitted,label", CONFIGS)
def test_simulated_machine_carries_the_reconciled_mass(model, fitted, label):
    p = load(model)
    tr = tractor.build(p)
    spec = mjcf.build(p, tr, terrain.build(p.course), fitted)
    m = mjcf.load(spec)
    assert sum(m.body_mass) == pytest.approx(tr.mass(fitted=fitted), abs=0.05)


@pytest.mark.parametrize("model", ["home", "pro"])
@pytest.mark.parametrize("fitted,label", CONFIGS)
def test_settled_axle_loads_match_the_static_calc(model, fitted, label):
    """The sim and the hand calc share masses and geometry: parked on the flat
    their axle loads must agree."""
    p = _flat(load(model))
    tr = tractor.build(p)
    spec = mjcf.build(p, tr, terrain.build(p.course), fitted)
    m = mjcf.load(spec)
    d = mujoco.MjData(m)
    mujoco.mj_step(m, d, nstep=int(5.0 / m.opt.timestep))
    rig = sim._Rig(spec, m, None)
    loads, strikes = rig.wheel_loads(d)
    calc = tr.axle_loads_n(fitted=fitted)
    for axle in ("front", "rear"):
        got = sum(v for k, v in loads.items() if k.startswith(axle))
        assert got == pytest.approx(calc[axle], rel=0.02)
    assert not strikes


def test_exported_model_round_trips(tmp_path):
    p = load("pro")
    tr = tractor.build(p)
    spec = mjcf.build(p, tr, terrain.build(p.course), DECK)
    mjcf.export(spec, tmp_path / "pro.xml")
    m = mujoco.MjModel.from_xml_path(str(tmp_path / "pro.xml"))
    assert np.abs(np.asarray(m.hfield_data) - spec.hfield).max() < 1e-6
    assert sum(m.body_mass) == pytest.approx(tr.mass(fitted=DECK), abs=0.05)


@pytest.fixture(scope="module")
def runs():
    out = {}
    for model in ("home", "pro"):
        p = load(model)
        tr = tractor.build(p)
        out[model] = (p, sim.run(p, tr, DECK))
    return out


def _ob(result, name):
    return next(o for o in result.obstacles if o.name == name)


def test_both_models_finish_the_course_with_the_deck(runs):
    for model, (p, r) in runs.items():
        assert r.completed and r.recoveries == 0, model
        assert not [o.name for o in r.obstacles if o.status == "FAIL"], model


def test_pro_rides_the_twist_on_its_trunnion_and_holds_the_side_slope(runs):
    p, r = runs["pro"]
    twist = _ob(r, "twist")
    assert twist.lift_s < p.course.scoring.wheel_lift_s
    assert twist.joint_extremes["trunnion"] <= p.layout.oscillation_max_deg + 0.5
    assert _ob(r, "side slope 17 deg").min_wheel_n > 300                     # uphill wheels stay loaded


def test_home_climbs_its_rated_slope_with_the_deck(runs):
    p, r = runs["home"]
    rated = _ob(r, f"climb {p.vehicle.max_slope_deg:g} deg")
    assert rated.rated and rated.outcome == "cleared"
    assert rated.peak_torque_x <= p.unit.peak_torque_factor + 0.01
    beyond = _ob(r, "climb 15 deg")
    assert beyond.status == "INFO"                                            # not rated for 15 deg


def test_home_front_axle_runs_out_of_roll_on_the_twist(runs):
    """Known finding: the leaf-sprung beam axle (+-40 mm REF) can't follow the
    twist, so a front wheel lifts. Update this if the axle gets a pivot."""
    p, r = runs["home"]
    twist = _ob(r, "twist")
    assert twist.status == "WARN" and twist.lift_wheel.startswith("front")


def test_report_and_figure_name_every_obstacle(runs):
    from eox import drawings
    p, r = runs["pro"]
    course = terrain.build(p.course)
    md = report.markdown(p, [r], course)
    svg = drawings.course_svg(p, course, [r], "dark")
    for o in r.obstacles:
        assert o.name in md and o.name in svg
    assert svg.startswith("<svg") and "</svg>" in svg


def test_a_climb_beyond_the_rating_is_information_only():
    p = load("home")
    p.course.obstacle = [types.SimpleNamespace(name="steep", kind="ramp", slope_deg=p.vehicle.max_slope_deg + 6,
                                               rise=0.3, length=1.0, crest_radius=2.0)]
    r = sim.run(p, tractor.build(p), (), keep_trajectory=False)
    assert r.obstacles[0].status == "INFO"
