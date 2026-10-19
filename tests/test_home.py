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


def test_bom_uses_front_axle_not_articulation(home):
    p, tr, _ = home
    rows, tot = bom.rollup(p, tr.box)
    assert "steer_axle" in tot["modules"] and "articulation" not in tot["modules"]
    assert next(r for r in rows if r["id"] == "D01")["qty_total"] == 1
