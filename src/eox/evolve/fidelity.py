"""Does a cheaper level of detail pick the same designs? (`uv run eox fidelity`)

Compares a trial run at full detail (trials/<name>/) with the same trial run at
a cheaper level (trials/<name>@<lod>/): each run's best designs are scored again
at the other level, then the two rankings are compared.

    rank agreement  Spearman correlation of the two levels' scores over the
                    designs both now have (1 = same order, 0 = unrelated)
    best overlap    how many of each run's top designs are in the other's top
    regret          how much worse, at full detail, the cheap run's best is than
                    the full run's best (0 = the cheap run found the same answer)
    captured        the share of the full run's improvement over today's design
                    that the cheap run's best achieves, scored at full detail.
                    This is the number to read: when the top designs score
                    almost the same, their order is noise and rank agreement
                    says little.
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from datetime import date

import numpy as np

from eox.evolve import engine
from eox.evolve.report import unique


def _load(path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            rec = json.loads(line)
            out[engine._key(rec["genes"])] = rec
    return out


def _job(args):
    from eox.evolve.evaluate import evaluate
    model, genes, configs = args
    return evaluate(model, genes, configs)


def _spearman(a, b) -> float:
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1]) if len(a) > 2 else float("nan")


def compare(name: str, lod: str, top: int = 10, workers: int | None = None, log=print) -> dict:
    hi_t = engine.load_trial(name)
    lo_t = engine.load_trial(name)
    lo_t.overrides["course.lod"] = lod
    hi, lo = _load(hi_t.out / "history.jsonl"), _load(lo_t.out / "history.jsonl")
    if not hi or not lo:
        raise FileNotFoundError(f"need both {hi_t.out}/history.jsonl and {lo_t.out}/history.jsonl: run the trial at both levels")
    rank = lambda t, recs: sorted((r for r in recs if "error" not in r), key=lambda r: engine.rank_key(t, r))  # noqa: E731
    hi_top = [r["genes"] for r in rank(hi_t, hi.values())[:top]]
    lo_top = [r["genes"] for r in rank(lo_t, lo.values())[:top]]

    # score each run's top designs at the other level (cached next to the cheap run)
    cross_path = lo_t.out / "cross.jsonl"
    at = {"high": dict(hi), lod: dict(lo)}
    if cross_path.exists():
        for line in cross_path.read_text().splitlines():
            c = json.loads(line)
            at[c["level"]][engine._key(c["genes"])] = c
    todo = [("high", g) for g in lo_top if engine._key(g) not in at["high"]] + \
           [(lod, g) for g in hi_top if engine._key(g) not in at[lod]]
    if todo:
        log(f"scoring {len(todo)} design(s) at the other level of detail")
        jobs = [(hi_t.model, {**hi_t.overrides, "course.lod": lv, **g}, hi_t.course_configs) for lv, g in todo]
        with ProcessPoolExecutor(max_workers=workers) as ex, open(cross_path, "a") as f:
            for (lv, g), res in zip(todo, ex.map(_job, jobs)):
                rec = {"level": lv, "genes": g, **res}
                f.write(json.dumps(rec) + "\n")
                at[lv][engine._key(g)] = rec

    designs = {engine._key(g): g for g in hi_top + lo_top}
    rows = []
    for k, g in designs.items():
        h, low = at["high"].get(k), at[lod].get(k)
        if h and low and "error" not in h and "error" not in low:
            rows.append((g, engine.score(hi_t, h), engine.violation(hi_t, h), engine.score(lo_t, low),
                         engine.violation(lo_t, low)))
    feasible = [r for r in rows if r[2] == 0 and r[4] == 0]
    rho = _spearman([r[1] for r in feasible], [r[3] for r in feasible])
    best_hi = min(rows, key=lambda r: (r[2] > 0, r[2], r[1]))
    best_lo = min(rows, key=lambda r: (r[4] > 0, r[4], r[3]))
    hi_keys = {engine._key(g) for g in hi_top}
    lo_keys = {engine._key(g) for g in lo_top}
    today = at["high"].get(engine._key(hi_t.baseline()))
    gain = (engine.score(hi_t, today) - best_hi[1]) if today and "error" not in today else float("nan")
    captured = (engine.score(hi_t, today) - best_lo[1]) / gain if gain and gain == gain else float("nan")
    out = dict(name=name, lod=lod, rho=rho, n=len(feasible), overlap=len(hi_keys & lo_keys), top=top,
               captured=captured, gain=gain,
               best_hi=best_hi, best_lo=best_lo, regret=best_lo[1] - best_hi[1],
               feasible_flip=sum(1 for r in rows if (r[2] == 0) != (r[4] == 0)), rows=rows,
               genes=[g.key for g in hi_t.genes], spread=float(np.std([r[1] for r in feasible])) if feasible else 0.0)
    return out


def markdown(c: dict) -> str:
    fmt = lambda v: str(v).lower() if isinstance(v, bool) else f"{v:g}" if isinstance(v, (int, float)) else str(v)  # noqa: E731
    L = [f"# Fidelity: `{c['name']}` at {c['lod']} detail against high", "",
         f"Generated {date.today().isoformat()} by `uv run eox fidelity --trial {c['name']} --lod {c['lod']}`. "
         f"Each run's top {c['top']} designs were scored again at the other level.", "",
         "| Measure | Value | Reading |", "|---|---|---|",
         f"| **Improvement captured** (the {c['lod']} run's best, scored at high) | **{c['captured'] * 100:.1f} %** | "
         f"of high's improvement over today's design ({c['gain']:.2f} points) |",
         f"| Rank agreement (Spearman, {c['n']} designs feasible at both levels) | {c['rho']:.2f} | 1 = same order |",
         f"| Top-{c['top']} overlap | {c['overlap']} of {c['top']} | designs both runs rank in their top {c['top']} |",
         f"| Regret: the {c['lod']} run's best, scored at high, minus high's best | {c['regret']:.2f} | "
         f"0 = same answer; score spread across these designs is {c['spread']:.2f} |",
         f"| Feasibility flips | {c['feasible_flip']} | designs that pass at one level and fail at the other |", "",
         *([f"The top designs score within {c['spread']:.2f} of each other, under "
            f"{c['spread'] / c['gain'] * 100:.0f} % of the improvement: their order is noise at either level, so "
            "rank agreement and overlap say little here. Read the improvement captured and the genes the two bests "
            "share.", ""] if c["gain"] == c["gain"] and c["gain"] and c["spread"] < 0.05 * c["gain"] else []),
         "| Gene | High's best | " + c["lod"].capitalize() + "'s best |", "|---|---|---|"]
    for k in c["genes"]:
        L.append(f"| `{k}` | {fmt(c['best_hi'][0][k])} | {fmt(c['best_lo'][0][k])} |")
    L += ["", "| Design | Score at high | Score at " + c["lod"] + " |", "|---|---|---|"]
    for g, sh, vh, sl, vl in sorted(c["rows"], key=lambda r: r[1])[:20]:
        L.append("| " + ", ".join(f"{k.split('.')[-1]}={fmt(v)}" for k, v in g.items()) +
                 f" | {sh:.2f}{' (fails)' if vh else ''} | {sl:.2f}{' (fails)' if vl else ''} |")
    return "\n".join(L) + "\n"
