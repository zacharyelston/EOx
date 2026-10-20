import pytest

from eox import bom, calcs, tractor
from eox.params import load

# Known FAILs tracked as GitHub issues; remove a group when its fix lands.
KNOWN_OPEN: set[str] = set()


@pytest.fixture(scope="module")
def home():
    p = load("home")
    tr = tractor.build(p)
    return p, tr, calcs.run(p, tr)


def test_home_shares_the_box_and_overrides_only_what_differs(home):
    p, tr, _ = home
    pro = load("pro")
    assert p.bus.units_installed == pro.bus.units_installed        # same box, same 4 branch glands
    assert p.bus.max_simultaneous_units == 2 < pro.bus.max_simultaneous_units
    assert set(vars(p.modes)) == {"mowing", "slope_mowing", "transport"}


def test_one_driven_axle_and_a_steering_front_axle(home):
    _, tr, _ = home
    assert tr.drive_units == 1 and not tr.articulated
    assert tr.axle("front").driven is False and tr.axle("rear").driven is True


def test_no_failures_outside_known_open_items(home):
    _, _, rep = home
    bad = [c.row() for c in rep.checks if c.status == "FAIL" and c.group not in KNOWN_OPEN]
    assert not bad


def test_front_axle_rolls_over_a_mid_mount_deck(home):
    _, _, rep = home
    c = next(c for c in rep.checks if c.group == "Deck")
    assert c.value > 0


def test_climbing_keeps_load_on_the_front_axle(home):
    _, _, rep = home
    c = next(c for c in rep.checks if c.name.startswith("front axle load climbing"))
    assert c.status in ("PASS", "WARN")


def test_home_is_geared_and_rated_for_the_deck(home):
    """Review P1 resolution: the 15:1 gear set is standard on Home (BOM G01)
    and its short-climb rating is 12 deg with the deck fitted, inside the
    rear-tyre grip limit. The Pro keeps the stock rear end."""
    p, tr, rep = home
    assert p.axle.ratio == 15.0 and load("pro").axle.ratio == 12.4
    assert p.vehicle.max_slope_deg == 12
    grip = next(c for c in rep.checks if c.name.startswith("steepest climb on grip"))
    assert grip.status == "PASS" and grip.value > p.vehicle.max_slope_deg
    rows, _ = bom.rollup(p, tr.box)
    assert next(r for r in rows if r["id"] == "G01")["qty_total"] == 1


def test_bom_uses_front_axle_not_articulation(home):
    p, tr, _ = home
    rows, tot = bom.rollup(p, tr.box)
    assert "steer_axle" in tot["modules"] and "articulation" not in tot["modules"]
    assert "gear_set" not in bom.rollup(load("pro"), tractor.build(load("pro")).box)[1]["modules"]
    assert next(r for r in rows if r["id"] == "D01")["qty_total"] == 1
