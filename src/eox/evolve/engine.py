"""Evolve a design: a seeded genetic algorithm over a trial's genes.

A trial (design/trials/<name>.toml) names the model, the genes (design values
allowed to change, with their ranges), the objectives (metrics to push up or
down, with weights) and the constraints (metrics that must stay in bounds).

Each generation keeps the best few designs unchanged (elitism) and breeds the
rest by tournament selection, uniform crossover and mutation. Designs are
ranked feasible-first: any constraint violation loses to every feasible
design; among feasible designs the lower score wins.

Runs are deterministic. The random generator is seeded and every evaluation
is cached in trials/<name>/history.jsonl by its genes, so re-running a trial
replays the cached designs instantly and only evaluates new ones. That is how
a trial resumes, or is extended with more generations.
"""

from __future__ import annotations

import json
import math
import os
import tomllib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from eox.evolve.evaluate import METRICS, evaluate
from eox.params import DESIGN, ROOT, load

TRIALS = DESIGN / "trials"
RESULTS = ROOT / "trials"


@dataclass
class Gene:
    key: str
    lo: float | None = None
    hi: float | None = None
    step: float | None = None
    choices: list | None = None
    why: str = ""

    def sample(self, rng):
        if self.choices is not None:
            return self.choices[rng.integers(len(self.choices))]
        return self._snap(rng.uniform(self.lo, self.hi))

    def contains(self, value) -> bool:
        if self.choices is not None:
            return value in self.choices
        return self.lo - 1e-9 <= float(value) <= self.hi + 1e-9

    def mutate(self, value, rng, sigma: float):
        if self.choices is not None:
            others = [c for c in self.choices if c != value]
            return others[rng.integers(len(others))] if others else value
        return self._snap(value + rng.normal(0.0, sigma * (self.hi - self.lo)))

    def _snap(self, x):
        x = min(max(float(x), self.lo), self.hi)
        if self.step:
            x = self.lo + round((x - self.lo) / self.step) * self.step
            x = round(min(x, self.hi), 6)
        return x


@dataclass
class Objective:
    metric: str
    goal: str            # "min" | "max"
    weight: float = 1.0
    scale: float = 1.0   # the metric's "one unit of caring"
    cap: float | None = None   # credit stops here: beyond it (above for "max", below for "min") is no better

    def value(self, m: dict) -> float:
        x = m[self.metric]
        if self.cap is not None:
            x = min(x, self.cap) if self.goal == "max" else max(x, self.cap)
        return x


@dataclass
class Constraint:
    metric: str
    min: float | None = None
    max: float | None = None


@dataclass
class Trial:
    name: str
    model: str
    question: str
    genes: list[Gene]
    objectives: list[Objective]
    constraints: list[Constraint]
    course_configs: tuple = ("deck",)
    population: int = 12
    generations: int = 8
    elite: int = 2
    seed: int = 1
    mutation: float = 0.2        # sigma as a fraction of each gene's range (halves by the last generation)
    mutation_rate: float = 0.35  # chance each gene mutates in a child
    crossover: float = 0.7
    patience: int = 8            # stop after this many generations without a better design (0: run them all)
    overrides: dict = field(default_factory=dict)   # fixed for every design in this trial (e.g. the ground)
    path: Path = None

    @property
    def lod(self) -> str:
        return self.overrides.get("course.lod", "high")

    @property
    def out(self) -> Path:
        """trials/<name>/, or trials/<name>@<lod>/ at a cheaper level of detail (its own cache)."""
        return RESULTS / (self.name if self.lod == "high" else f"{self.name}@{self.lod}")

    def baseline(self) -> dict:
        """The model's current values for every gene (with the trial's fixed overrides)."""
        p = load(self.model, self.overrides)
        out = {}
        for g in self.genes:
            node = p
            for part in g.key.split("."):
                node = node[int(part)] if part.isdigit() else getattr(node, part)
            out[g.key] = node
        return out


def load_trial(name: str) -> Trial:
    path = TRIALS / f"{name}.toml"
    if not path.exists():
        have = ", ".join(sorted(f.stem for f in TRIALS.glob("*.toml")))
        raise FileNotFoundError(f"design/trials/{name}.toml (trials: {have})")
    with open(path, "rb") as f:
        d = tomllib.load(f)["trial"]
    for o in d.get("objective", []) + d.get("constraint", []):
        if o["metric"] not in METRICS:
            raise KeyError(f"{name}: unknown metric '{o['metric']}' (have: {', '.join(METRICS)})")
    genes = [Gene(g["key"], g.get("min"), g.get("max"), g.get("step"), g.get("choices"), g.get("why", ""))
             for g in d["gene"]]
    t = Trial(d["name"], d["model"], d.get("question", ""), genes,
              [Objective(**o) for o in d.get("objective", [])], [Constraint(**c) for c in d.get("constraint", [])],
              tuple(d.get("course_configs", ["deck"])),
              **{k: d[k] for k in ("population", "generations", "elite", "seed", "mutation", "mutation_rate",
                                   "crossover", "patience") if k in d})
    t.overrides = dict(d.get("overrides", {}))
    clash = set(t.overrides) & {g.key for g in genes}
    if clash:
        raise KeyError(f"{name}: {sorted(clash)} is both a gene and a fixed override")
    t.path = path
    load(t.model, {**t.overrides, **{g.key: t.baseline()[g.key] for g in genes}})   # every key must exist
    return t


# ---------------------------------------------------------------------------
# ranking
# ---------------------------------------------------------------------------
def violation(trial: Trial, rec: dict) -> float:
    if "error" in rec:
        return math.inf
    m, v = rec["metrics"], 0.0
    for c in trial.constraints:
        x = m[c.metric]
        if c.max is not None and x > c.max:
            v += x - c.max
        if c.min is not None and x < c.min:
            v += c.min - x
    return v


def score(trial: Trial, rec: dict) -> float:
    """Weighted sum, lower is better: each objective in units of its scale."""
    if "error" in rec:
        return math.inf
    m = rec["metrics"]
    return sum(o.weight * (1 if o.goal == "min" else -1) * o.value(m) / o.scale for o in trial.objectives)


def rank_key(trial: Trial, rec: dict):
    v = violation(trial, rec)
    return (v > 0, v, score(trial, rec))


def _key(genes: dict) -> str:
    return json.dumps(genes, sort_keys=True)


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def _eval_job(args):
    model, genes, configs = args
    return evaluate(model, genes, configs)


def run(trial: Trial, workers: int | None = None, fresh: bool = False, log=print,
        evaluator=None) -> tuple[list[dict], dict]:
    """Evolve the trial. Returns every individual (one record per design per
    generation it appeared in) and the current design's record, for
    comparison. Evaluations are cached in history.jsonl. `evaluator`
    (model, genes, configs) -> record replaces the real one, in-process (tests)."""
    trial.out.mkdir(parents=True, exist_ok=True)
    hist_path = trial.out / "history.jsonl"
    if fresh and hist_path.exists():
        hist_path.unlink()
    cache: dict[str, dict] = {}
    if hist_path.exists():
        for line in hist_path.read_text().splitlines():
            rec = json.loads(line)
            cache[_key(rec["genes"])] = rec
    rng = np.random.default_rng(trial.seed)
    base = trial.baseline()
    workers = workers or max(1, (os.cpu_count() or 2) - 1)

    def evaluate_all(designs: list[dict]):
        todo = [g for g in {_key(g): g for g in designs}.values() if _key(g) not in cache]
        if todo:
            jobs = [(trial.model, {**trial.overrides, **g}, trial.course_configs) for g in todo]
            results = map(lambda j: evaluator(*j), jobs) if evaluator else pool.map(_eval_job, jobs)
            with open(hist_path, "a") as f:
                for g, res in zip(todo, results):
                    rec = {"genes": g, **res}
                    cache[_key(g)] = rec
                    f.write(json.dumps(rec) + "\n")

    def child(a: dict, b: dict, gen: int) -> dict:
        sigma = trial.mutation * (1 - 0.5 * gen / max(1, trial.generations - 1))
        for _ in range(8):
            c = {g.key: (b[g.key] if rng.random() < 0.5 else a[g.key]) if rng.random() < trial.crossover
                 else a[g.key] for g in trial.genes}
            for g in trial.genes:
                if rng.random() < trial.mutation_rate:
                    c[g.key] = g.mutate(c[g.key], rng, sigma)
            if _key(c) not in seen:
                break
            g = trial.genes[rng.integers(len(trial.genes))]          # a repeat: nudge one gene and retry
            a = {**c, g.key: g.mutate(c[g.key], rng, sigma)}
        return c

    pool = None if evaluator else ProcessPoolExecutor(max_workers=workers)   # one pool: each worker builds the box once
    individuals: list[dict] = []
    seen: set[str] = set()
    # the current design starts the population when it lies inside the genes' ranges; a trial that
    # explores elsewhere (e.g. the box at the front) still evaluates it, as the reference
    in_range = all(g.contains(base[g.key]) for g in trial.genes)
    log("reference: the current design" + ("" if in_range else " (outside the genes' ranges: compared, not bred)"))
    evaluate_all([base])
    reference = cache[_key(base)]
    pop = ([base] if in_range else []) + [{g.key: g.sample(rng) for g in trial.genes}
                                         for _ in range(trial.population - in_range)]
    best_key, stale = None, 0
    trial.stopped_at = None
    for gen in range(trial.generations):
        new = sum(1 for k in {_key(g) for g in pop} if k not in cache)
        evaluate_all(pop)
        recs = [{**cache[_key(g)], "generation": gen} for g in pop]
        seen.update(_key(g) for g in pop)
        recs.sort(key=lambda r: rank_key(trial, r))
        individuals += recs
        best = recs[0]
        k = rank_key(trial, best)
        improved = best_key is None or k < best_key
        best_key, stale = (k, 0) if improved else (best_key, stale + 1)
        scores = sorted(score(trial, r) for r in recs if violation(trial, r) == 0)
        median = f"{scores[len(scores) // 2]:.2f}" if scores else "-"
        log(f"gen {gen + 1:>2}/{trial.generations}: best {score(trial, best):.2f}"
            + (f" (violation {violation(trial, best):g})" if violation(trial, best) else "")
            + f", median {median}, {new} new design(s)"
            + ("" if improved else f", no better design for {stale} gen(s)"))
        if improved:
            log("   new best: " + ", ".join(f"{k_}={v}" for k_, v in best["genes"].items()))
        if gen == trial.generations - 1:
            break
        if trial.patience and stale >= trial.patience:
            trial.stopped_at = gen + 1
            log(f"stopping: no better design for {stale} generations")
            break

        def pick():
            i = min(rng.choice(len(recs), size=min(3, len(recs)), replace=False))   # recs are sorted: lower = better
            return recs[i]["genes"]

        nxt = [r["genes"] for r in recs[: trial.elite]]
        while len(nxt) < trial.population:
            nxt.append(child(pick(), pick(), gen + 1))
        pop = nxt
    if pool:
        pool.shutdown()
    return individuals, reference
