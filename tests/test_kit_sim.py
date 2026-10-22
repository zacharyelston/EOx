"""Kit mass conservation and rigid cradle mechanics before remote evolution."""
import mujoco
import pytest

from eox import calcs, tractor
from eox.kit_sim import layers
from eox.params import load
from eox.sim import mjcf, terrain
from eox.sim import run as sim
from eox.tractor import DECK


@pytest.fixture(scope="module")
def kit():
    p = load("home-kit")
    return p, tractor.build(p)


def test_steel_layers_are_counted_once_and_match_the_nested_inventory(kit):
    p, tr = kit
    masses, failed, moving = layers("B", "mild", 1750)
    assert failed == 0
    assert p.kit.layer_mass_kg == pytest.approx(sum(masses.values()))
    # Remove purchased steering/hub allowance from the beam, then recover
    # all fabricated steel from the rail, beam and front/rear layer masses.
    steel = sum(m.kg for m in tr.masses if "rail" in m.name or m.name.startswith("kit "))
    steel += next(m.kg for m in tr.masses if m.name == "front beam axle") - p.kit.front_purchased_mass_kg
    assert steel == pytest.approx(sum(masses.values()))
    assert p.steer_axle.mass_kg == pytest.approx(moving + p.kit.front_purchased_mass_kg)
    assert not [c.row() for c in calcs.run(p,tr).checks if c.status == "FAIL"]


def test_geometry_change_updates_frame_mass_sheet_fit_and_front_position():
    a = load("home-kit", {"layout.wheelbase": 1400})
    b = load("home-kit", {"layout.wheelbase": 1600})
    tractor.build(a)
    tractor.build(b)
    assert b.kit.layer_mass_kg > a.kit.layer_mass_kg
    assert a.layout.powerbox_x == a.layout.wheelbase+a.kit.powerbox_front_offset
    assert b.layout.powerbox_x == b.layout.wheelbase+b.kit.powerbox_front_offset
    assert a.layout.nose_x == a.layout.wheelbase-a.kit.nose_setback


@pytest.mark.parametrize("fitted", [(), DECK])
def test_rigid_pivot_has_roll_without_vertical_suspension_and_conserves_mass(kit, fitted):
    p, tr = kit
    spec = mjcf.build(p, tr, terrain.build(p.course), fitted)
    m = mjcf.load(spec)
    assert mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "bounce") == -1
    assert mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "axle_roll") >= 0
    assert "bounce" not in spec.joints
    assert sum(m.body_mass) == pytest.approx(tr.mass(fitted=fitted), abs=.05)


def test_legacy_leaf_spring_model_is_preserved():
    p = load("home")
    spec = mjcf.build(p, tractor.build(p), terrain.build(p.course))
    assert "bounce" in spec.joints


def test_parked_kit_axle_loads_match_static_calculation():
    p = load("home-kit")
    p.course.obstacle = []
    p.course.run_in = 10
    tr = tractor.build(p)
    spec = mjcf.build(p, tr, terrain.build(p.course), DECK)
    m = mjcf.load(spec)
    d = mujoco.MjData(m)
    mujoco.mj_step(m, d, nstep=int(5/m.opt.timestep))
    rig = sim._Rig(spec, m, None)
    loads, strikes = rig.wheel_loads(d)
    for axle, expected in tr.axle_loads_n(fitted=DECK).items():
        assert sum(n for name,n in loads.items() if name.startswith(axle)) == pytest.approx(expected,rel=.02)
    assert not strikes
