import pytest

from eox import bom, calcs, powerbox
from eox.params import load

# Checks that are known to fail and are tracked as open issues in
# docs/powerbox.md. Remove a group from here when its fix lands.
KNOWN_OPEN: set[str] = set()


@pytest.fixture(scope="module")
def design():
    p = load()
    lay = powerbox.build(p)
    return p, lay, calcs.run(p, lay)


def test_every_part_is_manufacturable_at_scs(design):
    _, _, rep = design
    bad = [c.row() for c in rep.checks if c.group.startswith("SCS ") and c.status == "FAIL"]
    assert not bad


def test_no_failures_outside_known_open_items(design):
    _, _, rep = design
    bad = [c.row() for c in rep.checks if c.status == "FAIL" and c.group not in KNOWN_OPEN]
    assert not bad


def test_components_fit_inside_shells(design):
    _, _, rep = design
    assert all(c.status != "FAIL" for c in rep.checks if c.group == "Layout")


def test_selv_holds_under_single_fault(design):
    _, _, rep = design
    c = next(c for c in rep.checks if "single fault" in c.name)
    assert c.value <= 60.0


def test_motor_holes_line_up_through_wall_and_doubler(design):
    p, lay, _ = design
    tray, doubler = lay.part("PB-101"), lay.part("PB-103")
    wall = sorted((round(h.s - lay.x.motor_x, 6), round(h.h - lay.x.motor_z, 6))
                  for h in tray.holes if h.label == "motor bolt")
    plate = sorted((round(h.s, 6), round(h.h, 6)) for h in doubler.holes if h.label == "motor bolt")
    assert len(wall) == p.motor.bolt_count and wall == plate


def test_cover_screws_line_up_with_tray_rivnuts(design):
    p, lay, _ = design
    tray, cover = lay.part("PB-101"), lay.part("PB-102")
    tz = {round(h.h, 3) for h in tray.holes if "cover screw" in h.label}
    cz = {round(lay.z_top - h.h, 3) for h in cover.holes if "cover screw" in h.label}
    assert tz == cz
    assert sum("cover screw" in h.label for h in tray.holes) == sum("cover screw" in h.label for h in cover.holes)


def test_bom_rolls_up_both_sources(design):
    _, lay, _ = design
    rows, tot = bom.rollup(lay)
    ids = {r["id"] for r in rows}
    assert {"PB-101", "PB-102", "E01", "E02", "E03"} <= ids
    assert tot["purchased_usd"] > 0 and tot["mass_kg"] > 45


def test_bulkhead_rivets_line_up_with_floor_holes(design):
    p, lay, _ = design
    floor = sorted((round(h.s, 3), round(h.h, 3)) for h in lay.part("PB-101").holes if h.label == "rivet, bulkhead")
    flange = sorted((round(lay.x.bh_x + h.h, 3), round(h.s, 3)) for h in lay.part("PB-106").holes
                    if h.label == "rivet to floor")
    assert len(floor) == p.bulkhead.rivets and floor == flange


def test_bulkhead_splits_battery_from_motor_bay(design):
    p, lay, _ = design
    bat_x1 = lay.body("battery").bounds()[1]
    bay_x0 = min(lay.body(n).bounds()[0] for n in ("motor", "controller", "electrics", "fan"))
    assert bat_x1 < lay.x.bh_x
    assert lay.x.bh_x + p.bulkhead.flange <= bay_x0


def test_dead_fan_keeps_pack_under_rating(design):
    p, _, rep = design
    c = next(c for c in rep.checks if c.name == "pack temp, mowing, fan failed")
    assert c.value <= p.battery.max_temp_discharge_c


def test_inlet_slots_stay_in_motor_bay(design):
    _, lay, _ = design
    slots = [h for h in lay.part("PB-101").holes if h.label == "inlet slot"]
    assert slots and all(h.s - h.length / 2 > lay.x.bh_x + 20 for h in slots)
