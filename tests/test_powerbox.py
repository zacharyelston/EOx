import pytest

from eox import bom, calcs, tractor
from eox.params import load


@pytest.fixture(scope="module")
def design():
    p = load("pro")
    tr = tractor.build(p)
    return p, tr, calcs.run(p, tr)


def test_every_box_part_is_manufacturable_at_scs(design):
    _, _, rep = design
    bad = [c.row() for c in rep.checks if c.group.startswith("SCS ") and c.status == "FAIL"]
    assert not bad


def test_components_fit_inside_shells(design):
    _, _, rep = design
    assert all(c.status != "FAIL" for c in rep.checks if c.group == "Box layout")


def test_one_branch_gland_per_unit(design):
    p, tr, _ = design
    glands = [h for h in tr.box.part("PB-101").holes if h.label == "unit branch gland"]
    assert len(glands) == p.bus.units_installed


def test_cover_screws_line_up_with_tray_rivnuts(design):
    _, tr, _ = design
    box = tr.box
    tray, cover = box.part("PB-101"), box.part("PB-102")
    tz = {round(h.h, 3) for h in tray.holes if "cover screw" in h.label}
    cz = {round(box.z_top - h.h, 3) for h in cover.holes if "cover screw" in h.label}
    assert tz == cz
    assert sum("cover screw" in h.label for h in tray.holes) == sum("cover screw" in h.label for h in cover.holes)


def test_bom_multiplies_by_module_count(design):
    p, tr, _ = design
    rows, tot = bom.rollup(p, tr.box)
    rear_end = next(r for r in rows if r["id"] == "D01")
    assert rear_end["qty_total"] == p.bom.drive_axle * int(rear_end["qty"])
    assert {"powerbox", "drive_axle", "articulation", "controls"} <= set(tot["modules"])
    assert any(r["id"] == "PB-101" for r in rows)
