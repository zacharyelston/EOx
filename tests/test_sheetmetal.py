import math

import pytest
from build123d import Vector

from eox.params import gauge, load, load_materials
from eox.sheetmetal import IN, FlangedPanel, Hole


@pytest.fixture(scope="module")
def g():
    return load().gauge


def test_bend_deduction_matches_scs_published_tables():
    mats = load_materials()
    for name in ("al_5052_h32", "mild_steel", "ss_304"):
        for row in mats[name]["gauges"]:
            if not row["bd_in"]:
                continue
            gg = gauge(mats, name, row["t_in"] * IN)
            # SCS's published BD is rounded/empirical and differs from its own
            # K and R by up to 0.0035" (0.063" 5052) -- well inside the
            # +-0.015" bend tolerance. STEP uploads are unfolded with K and R.
            assert gg.bd / IN == pytest.approx(row["bd_in"], abs=0.004), (name, row["t_in"])


def test_u_channel_flat_width(g):
    u = FlangedPanel("U", "u", 200, 100, g, {"+v": 30, "-v": 30})
    fx, fy = u.flat_bbox()
    assert fx == pytest.approx(200)
    assert fy == pytest.approx(100 + 2 * 30 - 2 * g.bd)


def test_solid_is_one_valid_body_matching_flat_volume(g):
    tray = FlangedPanel("T", "t", 300, 200, g, {e: 60 for e in ("+u", "-u", "+v", "-v")},
                        holes=[Hole("base", 0, 0, 20)])
    s = tray.solid()
    assert s.is_valid and len(s.solids()) == 1
    bb = s.bounding_box().size
    assert (bb.X, bb.Y, bb.Z) == pytest.approx((300, 200, 60))
    # bend zones differ slightly between neutral-axis flat and true arc volume
    assert s.volume == pytest.approx(tray.flat_area_mm2() * g.t, rel=0.01)


@pytest.mark.parametrize("edge,hole_pt", [
    ("+v", (50, 100, 35)), ("-v", (-50, -100, 35)), ("+u", (150, 20, 35)), ("-u", (-150, -20, 35)),
])
def test_flange_holes_land_where_specified(g, edge, hole_pt):
    s_along = hole_pt[0] if edge[1] == "v" else hole_pt[1]
    tray = FlangedPanel("T", "t", 300, 200, g, {e: 60 for e in ("+u", "-u", "+v", "-v")},
                        holes=[Hole(edge, s_along, 35, 10)])
    x, y, z = hole_pt
    inset = g.t / 2
    x -= math.copysign(inset, x) if edge[1] == "u" else 0
    y -= math.copysign(inset, y) if edge[1] == "v" else 0
    solid = tray.solid()
    assert not solid.is_inside(Vector(x, y, z))           # hole
    assert solid.is_inside(Vector(x, y, z + 12))          # wall above it


def test_corners_are_closed_to_corner_gap(g):
    tray = FlangedPanel("T", "t", 300, 200, g, {e: 60 for e in ("+u", "-u", "+v", "-v")}, corner_gap=0.5)
    s = tray.solid()
    assert s.is_inside(Vector(149, 100 - g.t / 2, 40))         # long flange reaches the corner
    assert s.is_inside(Vector(150 - g.t / 2, 100 - g.t - 1.0, 40))  # short flange reaches its neighbour


def test_scs_checks_flag_deep_u_channel(g):
    deep = FlangedPanel("D", "deep", 300, 100, g, {"+v": 80, "-v": 80})
    rule = [c for c in deep.scs_checks(load().scs) if "U-channel" in c.name]
    assert rule and rule[0].status == "FAIL"


def test_slot_cuts_solid_and_flat(g):
    plate = FlangedPanel("S", "slot", 200, 100, g, {"+v": 40},
                         holes=[Hole("base", 0, 0, 8, length=30), Hole("+v", 0, 25, 8, length=30)])
    solid = plate.solid()
    assert not solid.is_inside(Vector(14, 0, g.t / 2))          # inside base slot, near one end
    assert solid.is_inside(Vector(25, 0, g.t / 2))              # past the slot end
    assert not solid.is_inside(Vector(14, 50 - g.t / 2, 25))    # flange slot runs along x too
    full = FlangedPanel("S", "slot", 200, 100, g, {"+v": 40})
    assert full.flat_area_mm2() - plate.flat_area_mm2() == pytest.approx(2 * (math.pi * 16 + 8 * 30))
    assert plate.flat_face().area == pytest.approx(plate.flat_area_mm2(), rel=1e-6)
