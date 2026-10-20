"""Design trials (src/eox/evolve): genes, ranking, the engine's determinism
and caching, the layout checks a front-mounted box needs, and the committed
home-front-battery result."""
import json
import tomllib

import numpy as np
import pytest

from eox import calcs, tractor
from eox.evolve import engine
from eox.evolve.evaluate import evaluate
from eox.params import ROOT, load

TRIAL = """
[trial]
name = "synthetic"
model = "home"
question = "test"
population = 8
generations = 6
seed = 3
[[trial.gene]]
key = "layout.powerbox_x"
min = 400
max = 2000
step = 10
[[trial.gene]]
key = "deck.pto_unit_y"
choices = [430, -430]
[[trial.objective]]
metric = "grip_limit_deg"
goal = "max"
[[trial.constraint]]
metric = "calc_fails"
max = 0
"""


def _fake(model, genes, configs):
    """A known landscape: best at x = 1200 on the -430 side; infeasible past 1800."""
    x = genes["layout.powerbox_x"]
    grip = 20 - ((x - 1200) / 100) ** 2 - (0 if genes["deck.pto_unit_y"] == -430 else 1)
    return {"metrics": {"grip_limit_deg": grip, "calc_fails": float(x > 1800)}, "fails": [], "warns": []}


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "synthetic.toml").write_text(TRIAL)
    monkeypatch.setattr(engine, "TRIALS", tmp_path / "design")
    monkeypatch.setattr(engine, "RESULTS", tmp_path / "results")
    return engine.load_trial("synthetic")


def test_genes_stay_in_range_and_on_step(synthetic):
    rng = np.random.default_rng(0)
    g = synthetic.genes[0]
    for _ in range(200):
        x = g.mutate(g.sample(rng), rng, 0.5)
        assert g.lo <= x <= g.hi and (x - g.lo) % g.step == 0


def test_overrides_reach_list_items_and_reject_unknown_keys():
    assert load("home", {"layout.operator_cg.0": 300}).layout.operator_cg[0] == 300
    with pytest.raises(KeyError):
        load("home", {"layout.no_such_value": 1})


def test_a_trial_must_name_known_metrics(tmp_path, monkeypatch):
    (tmp_path / "bad.toml").write_text(TRIAL.replace('metric = "grip_limit_deg"', 'metric = "speed"'))
    monkeypatch.setattr(engine, "TRIALS", tmp_path)
    with pytest.raises(KeyError):
        engine.load_trial("bad")


def test_feasible_designs_rank_first(synthetic):
    ok = {"metrics": {"grip_limit_deg": 1.0, "calc_fails": 0.0}}
    better_but_broken = {"metrics": {"grip_limit_deg": 50.0, "calc_fails": 1.0}}
    assert engine.rank_key(synthetic, ok) < engine.rank_key(synthetic, better_but_broken)


def test_engine_finds_the_optimum_and_replays_from_its_cache(synthetic):
    calls = []

    def counted(*a):
        calls.append(a[1])
        return _fake(*a)

    inds, ref = engine.run(synthetic, evaluator=counted, log=lambda *a: None)
    best = min(inds, key=lambda r: engine.rank_key(synthetic, r))
    assert abs(best["genes"]["layout.powerbox_x"] - 1200) <= 100 and best["genes"]["deck.pto_unit_y"] == -430
    first = len(calls)
    inds2, _ = engine.run(synthetic, evaluator=counted, log=lambda *a: None)
    assert len(calls) == first                                   # same seed, all cached: nothing re-evaluated
    assert [r["genes"] for r in inds2] == [r["genes"] for r in inds]
    lines = (synthetic.out / "history.jsonl").read_text().splitlines()
    assert len(lines) == first and all("metrics" in json.loads(x) for x in lines)


def _fails(genes):
    p = load("home", genes)
    rep = calcs.run(p, tractor.build(p))
    return {c.name.split(" (")[0] for c in rep.checks if c.status == "FAIL"}


def test_a_front_box_must_clear_the_steered_tyres_and_sit_on_the_frame():
    low = _fails({"layout.powerbox_x": 1600, "layout.powerbox_z": 340})
    assert any(f.startswith("steered front tyres clear every part") for f in low)
    hanging = _fails({"layout.powerbox_x": 2200, "layout.powerbox_z": 640})
    assert any(f.startswith("power box sits within the frame") for f in hanging)


def test_the_committed_front_battery_result_still_holds():
    """trials/home-front-battery/best.toml must still evaluate as feasible.
    If the model changes, re-run the trial and commit its new results."""
    with open(ROOT / "trials" / "home-front-battery" / "best.toml", "rb") as f:
        genes = tomllib.load(f)["overrides"]
    r = evaluate("home", genes)
    assert "error" not in r
    assert r["metrics"]["calc_fails"] == 0 and r["metrics"]["course_fails"] == 0, r["fails"]
    assert r["metrics"]["grip_limit_deg"] >= load("home").vehicle.max_slope_deg
