"""Tyres (src/eox/tyres.py): deflection, grip and rolling resistance from tyre
size, pressure, load and ground; and the simulated tyre's squash."""
import math
import types

import mujoco
import pytest

from eox import calcs, tractor, tyres
from eox.params import load
from eox.sim import mjcf, terrain
from eox.tractor import DECK

LAWN = types.SimpleNamespace(cone_index_kpa=400, design_slip=0.12, carcass_kpa=15, max_deflection_ratio=0.25)
SOFT = types.SimpleNamespace(**{**vars(LAWN), "cone_index_kpa": 200})
REAR = tyres.Tyre(457, 216, 203, 83)          # 18x8.50-8 at 12 psi


def test_deflection_is_load_over_membrane_stiffness():
    k = (83 + 15) * 1000 * math.pi * math.sqrt(0.457 * 0.216)
    assert tyres.stiffness(REAR, LAWN) == pytest.approx(k)
    assert tyres.deflection(REAR, 1260, LAWN) == pytest.approx(1260 / k * 1000)


def test_softer_tyres_grip_more_and_roll_easier():
    soft, hard = tyres.Tyre(457, 216, 203, 55), tyres.Tyre(457, 216, 203, 138)
    W = 1260
    assert tyres.deflection(soft, W, LAWN) > tyres.deflection(hard, W, LAWN)
    assert tyres.grip(soft, W, LAWN) > tyres.grip(hard, W, LAWN)
    assert tyres.rolling(soft, W, LAWN) < tyres.rolling(hard, W, LAWN)


def test_soft_ground_grips_less_and_drags_more():
    W = 1260
    assert tyres.grip(REAR, W, SOFT) < tyres.grip(REAR, W, LAWN)
    assert tyres.rolling(REAR, W, SOFT) > tyres.rolling(REAR, W, LAWN)


def test_lawn_is_calibrated_to_the_old_turf_values():
    """design/ground.toml's cone index was chosen so an EOX drive tyre at its
    design pressure gives about the turf values the calcs used before (0.5, 0.1)."""
    p = load("home")
    tr = tractor.build(p)
    t = tr.tyres["rear"]
    assert t["grip"] == pytest.approx(0.5, abs=0.03)
    assert t["rolling"] == pytest.approx(0.09, abs=0.015)


def test_an_underinflated_tyre_fails_the_deflection_check():
    p = load("home", {"axle.tire_pressure_kpa": 10})
    rep = calcs.run(p, tractor.build(p))
    c = next(c for c in rep.checks if c.group == "Tyres" and c.name.startswith("rear tyres"))
    assert c.status == "FAIL"


def test_the_simulated_tyre_carries_its_load_at_the_design_height():
    """The tyre spring is preloaded by the static deflection, so parked the
    machine sits at its design heights (deck clearance etc. are parked values)."""
    p = load("home")
    p.course.obstacle = []
    p.course.run_in = 10.0
    tr = tractor.build(p)
    spec = mjcf.build(p, tr, terrain.build(p.course), DECK)
    m = mjcf.load(spec)
    d = mujoco.MjData(m)
    mujoco.mj_step(m, d, nstep=int(4.0 / m.opt.timestep))
    for axle in ("rear", "front"):
        j = m.joint(f"{axle}_L:tyre")
        assert m.qpos_spring[m.jnt_qposadr[j.id]] == pytest.approx(-tr.tyres[axle]["deflection_mm"] / 1000, rel=1e-3)
        sim = sum(float(d.joint(f"{axle}_{s}:tyre").qpos[0]) for s in "LR") / 2 * 1000
        assert abs(sim) < 0.25 * tr.tyres[axle]["deflection_mm"]          # settles near the design height
