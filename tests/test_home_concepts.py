"""Nesting evidence must account for every blank, spacing and rotation."""
from dataclasses import replace
import tomllib

import pytest

from eox.home_concepts import pack, study, validate_nest
from eox.params import ROOT, gauge, load_materials
from eox.sheetmetal import FlangedPanel


@pytest.fixture
def plates():
    g = gauge(load_materials(), "mild_steel", .119*25.4)
    return [FlangedPanel("P", "test plate", 60, 20, g, qty=2)]


def test_rotation_is_required_and_gap_is_preserved(plates):
    # Only the 20 x 60 orientation fits. Two boxes need the full 4 mm gap.
    placed = pack(plates, 56, 72, edge=6, gap=4)
    assert placed is not None
    assert all(p.rotated for p in placed)
    assert abs(placed[0].x-placed[1].x) == pytest.approx(24)
    assert pack(plates, 55, 72, edge=6, gap=4) is None


def test_missing_or_repeated_instances_are_rejected(plates):
    placed = pack(plates, 56, 72)
    with pytest.raises(ValueError, match="missing / repeated"):
        validate_nest(plates, placed[:1], 56, 72, 6, 4)
    with pytest.raises(ValueError, match="missing / repeated"):
        validate_nest(plates, [placed[0], placed[0]], 56, 72, 6, 4)


def test_invalid_geometric_evidence_is_rejected(plates):
    placed = pack(plates, 56, 72)
    for field, value, reason in [("x", 5, "edge margin"), ("h", 59, "wrong envelope"),
                                 ("y", 7, "outside sheet")]:
        bad = [replace(placed[0], **{field: value}), placed[1]]
        with pytest.raises(ValueError, match=reason):
            validate_nest(plates, bad, 56, 72, 6, 4)
    with pytest.raises(ValueError, match="overlap / gap"):
        validate_nest(plates, [placed[0], replace(placed[1], x=placed[0].x+23)], 56, 72, 6, 4)


def test_all_published_layers_fit_both_materials_and_bend_screens():
    with (ROOT/"design/home-concepts.toml").open("rb") as f:
        config = tomllib.load(f)
    results = study(config)
    assert len(results) == 6
    assert sum(len(r["layers"]) for r in results) == 20
    for result in results:
        for layer in result["layers"]:
            assert layer["nest"] is not None, (result["material"], result["concept"], layer["name"])
            assert not layer["failures"]
            validate_nest(layer["parts"], layer["nest"], 1422.4, 863.6, 6, 4)


def test_steel_variants_regenerate_bend_dependent_blanks():
    with (ROOT/"design/home-concepts.toml").open("rb") as f:
        results = study(tomllib.load(f))
    a = next(r for r in results if r["material"]["id"] == "mild" and r["concept"]["id"] == "B")
    b = next(r for r in results if r["material"]["id"] == "304" and r["concept"]["id"] == "B")
    assert a["layers"][0]["parts"][0].flat_bbox() != b["layers"][0]["parts"][0].flat_bbox()
    assert sum(l["mass"] for l in b["layers"]) > sum(l["mass"] for l in a["layers"])
