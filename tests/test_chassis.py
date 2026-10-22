import copy
import math
import tomllib

import pytest

from eox.chassis import Section, sweep
from eox.params import ROOT


def test_section_properties_have_correct_geometric_scaling():
    a = Section(120, 50, 20, 2)
    b = Section(240, 100, 40, 4)
    assert b.shell_area == pytest.approx(a.shell_area * 4)
    assert b.shell_i == pytest.approx(a.shell_i * 16)
    assert b.modulus == pytest.approx(a.modulus * 8)


@pytest.mark.parametrize("bad", [0, -1, math.inf, math.nan])
def test_nonphysical_sections_are_rejected(bad):
    with pytest.raises(ValueError):
        Section(bad, 50, 20, 2)


def test_beam_load_changes_stress_and_deflection_without_changing_mass():
    with (ROOT / "design/chassis-study.toml").open("rb") as f:
        config = tomllib.load(f)
    heavier = copy.deepcopy(config)
    heavier["study"]["gross_vehicle_mass_kg"] *= 2
    key = lambda r: (r["depth_mm"], r["width_mm"], r["lip_mm"], r["thickness_mm"])
    normal = {key(r): r for r in sweep(config)}
    doubled = {key(r): r for r in sweep(heavier)}
    for k, a in normal.items():
        b = doubled[k]
        assert b["stress_mpa"] == pytest.approx(a["stress_mpa"] * 2)
        assert b["deflection_mm"] == pytest.approx(a["deflection_mm"] * 2)
        assert b["estimated_rail_kit_kg"] == a["estimated_rail_kit_kg"]


def test_deep_narrow_channel_is_rejected_by_tooling_screen():
    with (ROOT / "design/chassis-study.toml").open("rb") as f:
        config = tomllib.load(f)
    config["search"] = {"thickness_in": [0.119], "web_depth_mm": [80],
                        "rail_width_mm": [60], "return_lip_mm": [20]}
    result, = sweep(config)
    assert not result["screen_pass"]
    assert "channel tooling clearance" in result["reasons"]
