import math

import pytest

from eox import calcs, tractor
from eox.calcs.vehicle import tip_angle
from eox.params import load

# Checks known to fail, tracked as GitHub issues. Remove a group when its fix lands.
KNOWN_OPEN: set[str] = set()


@pytest.fixture(scope="module")
def pro():
    p = load("pro")
    tr = tractor.build(p)
    return p, tr, calcs.run(p, tr)


def _check(rep, name):
    return next(c for c in rep.checks if c.name == name)


def test_loader_merges_shared_and_model_files():
    p = load("pro")
    assert p.model.layout == "articulated" and p.unit.rated_power_w > 0 and p.battery.cells_series == 16


def test_loader_rejects_unknown_model():
    with pytest.raises(FileNotFoundError):
        load("nope")


def test_tip_angle_matches_hand_calc_for_a_box():
    # half-track w, CG height h: side tip angle = atan(w / h)
    w, h, L = 400.0, 500.0, 1000.0
    pts = [(L / 2, w, 0), (L / 2, -w, 0), (-L / 2, -w, 0), (-L / 2, w, 0)]
    edges = list(zip(pts, pts[1:] + pts[:1]))
    assert tip_angle((0, 0, h), edges) == pytest.approx(math.degrees(math.atan(w / h)), abs=0.5)


def test_no_failures_outside_known_open_items(pro):
    _, _, rep = pro
    bad = [c.row() for c in rep.checks if c.status == "FAIL" and c.group not in KNOWN_OPEN]
    assert not bad


def test_mass_and_axle_loads_are_consistent(pro):
    p, tr, _ = pro
    loads = tr.axle_loads_n()
    assert sum(loads.values()) == pytest.approx(tr.mass() * 9.81)
    assert all(v > 0 for v in loads.values())


def test_articulation_moves_only_the_front_half(pro):
    _, tr, _ = pro
    assert tr.contacts("rear", 35) == tr.contacts("rear", 0)
    assert tr.contacts("front", 35) != tr.contacts("front", 0)
    assert tr.cg("rear", 35) == pytest.approx(tr.cg("rear", 0))


def test_no_mode_runs_more_units_than_the_bus_carries(pro):
    p, _, rep = pro
    for c in rep.checks:
        if c.group.startswith("Mode ") and c.name == "units running":
            assert c.value <= p.bus.max_simultaneous_units


def test_halves_clear_each_other_at_full_lock(pro):
    _, _, rep = pro
    c = next(c for c in rep.checks if c.group == "Pivot" and c.name.startswith("front and rear halves"))
    assert c.value == 0, c.note


def test_controllers_sit_on_the_centreline(pro):
    _, tr, _ = pro
    ys = [b.center[1] for _, k, b in tr.bodies if k == "controller"]
    assert len(ys) == 2 and all(abs(y) < 1e-6 for y in ys)


def test_hydraulic_steering_is_strong_and_fast_enough(pro):
    _, _, rep = pro
    assert _check(rep, "lock-to-lock time (4 L/min)").status == "PASS"
    assert next(c for c in rep.checks if c.name.startswith("cylinder moment")).status in ("PASS", "WARN")


def test_extra_reduction_lowers_motor_torque(pro):
    p, tr, _ = pro
    from eox.calcs.drive import _per_motor
    t1, t2 = _per_motor(p, tr, 10, 1.0), _per_motor(p, tr, 10, 2.0)
    assert t2 < t1 / 1.9


@pytest.mark.parametrize("model", ["pro", "home"])
def test_golf_cart_motors_sit_sideways_and_nothing_overlaps(model):
    """Golf-cart motors mount parallel to the axle on an off-centre gear case
    (docs/research/golf-cart.md); every model's parts must clear each other."""
    from eox.calcs.vehicle import parts_overlap
    p = load(model)
    tr = tractor.build(p)
    motors = [b for _, k, b in tr.bodies if k == "motor"]
    assert motors and all(b.shape == "cyl_y" for b in motors)
    gear_cases = [b for _, k, b in tr.bodies if b.name == "rear end"]
    assert all(abs(b.center[1] - p.axle.diff_offset_y) < 1e-6 for b in gear_cases)
    assert parts_overlap(tr) == []
