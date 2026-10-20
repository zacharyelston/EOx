"""Reference machines (src/eox/reference.py): the lumped model reproduces the
spec it was built from, and every committed reference builds and drives."""
import shutil

import pytest

from eox import reference
from eox.tractor import DECK

DATA = __import__("pathlib").Path(__file__).parent / "data"


@pytest.fixture
def placeholder(tmp_path, monkeypatch):
    shutil.copy(DATA / "reference-placeholder.toml", tmp_path / "placeholder.toml")
    monkeypatch.setattr(reference, "REFERENCE", tmp_path)
    p = reference.load("placeholder")
    return p, reference.build(p)


def test_lumps_reproduce_mass_split_and_cg_height(placeholder):
    p, tr = placeholder
    s, e = p.spec, p.estimate
    empty = [m for m in tr._counted(None, DECK) if m.name != "operator"]
    M = sum(m.kg for m in empty)
    assert M == pytest.approx(s.mass_kg)
    x = sum(m.kg * m.cg[0] for m in empty) / M
    z = sum(m.kg * m.cg[2] for m in empty) / M
    assert x / s.wheelbase == pytest.approx(e.front_share, abs=1e-6)
    assert z == pytest.approx(e.cg_height, abs=1e-6)


def test_the_deck_is_the_only_tagged_mass(placeholder):
    p, tr = placeholder
    assert tr.mass(fitted=DECK) - tr.mass() == pytest.approx(p.estimate.deck_mass_kg)


@pytest.mark.parametrize("name", reference.NAMES)
def test_every_reference_builds_with_sourced_core_specs(name):
    p = reference.load(name)
    tr = reference.build(p)
    assert tr.mass(fitted=DECK) - p.vehicle.mass_operator_kg == pytest.approx(p.spec.mass_kg, rel=1e-6)
    assert all(hasattr(p.spec, k) for k in ("wheelbase", "front_tire", "rear_tire", "price_usd"))
    assert hasattr(p.model, "sources")                                          # where the numbers came from
