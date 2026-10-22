"""A trial's results: the answer, the leaderboard, best.toml and a progress figure."""

from __future__ import annotations

import json
from datetime import date

from eox.drawings import THEMES, Svg
from eox.evolve.engine import Trial, rank_key, score, violation
from eox.evolve.evaluate import METRICS

SHOWN = ("grip_limit_deg", "climb_torque_x", "working_slope_deg", "course_warns", "wheel_lift_s", "deck_float_mm",
         "side_slope_wheel_n", "mass_kg", "cost_usd", "mowing_runtime_h", "calc_fails", "calc_warns", "course_fails")


def _fmt(x) -> str:
    if isinstance(x, bool) or x is None:
        return str(x).lower()
    if isinstance(x, float):
        return f"{x:,.0f}" if abs(x) >= 100 else f"{x:.2f}".rstrip("0").rstrip(".")
    return str(x)


def unique(individuals: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in individuals:
        k = json.dumps(r["genes"], sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def best(trial: Trial, individuals: list[dict]) -> dict:
    return min(unique(individuals), key=lambda r: rank_key(trial, r))


def best_toml(trial: Trial, top: dict, reference: dict) -> str:
    lines = [f"# Trial {trial.name}: the best design's changed values, as [overrides] for",
             f"# design/models/{trial.model}.toml. Review before adopting: a trial is evidence, not a decision.",
             f"# Score {score(trial, top):.2f} (today {score(trial, reference):.2f}; lower is better).", "",
             "[overrides]"]
    changed = [(f'"{k}" = {str(v).lower() if isinstance(v, bool) else repr(v)}', reference["genes"].get(k))
               for k, v in top["genes"].items() if v != reference["genes"].get(k)]
    w = max((len(a) for a, _ in changed), default=0)
    lines += [f"{a:<{w}}  # today: {_fmt(b)}" for a, b in changed]
    return "\n".join(lines) + "\n"


def markdown(trial: Trial, individuals: list[dict], reference: dict) -> str:
    uniq = unique(individuals)
    feasible = [r for r in uniq if violation(trial, r) == 0]
    top = best(trial, individuals)
    secs = sum(r.get("elapsed_s", 0) for r in uniq)
    L = [f"# Trial: {trial.name}", "",
         f"**Question.** {trial.question}", "",
         f"Generated {date.today().isoformat()} by `uv run eox evolve --trial {trial.name}` from "
         f"`design/trials/{trial.name}.toml`: {trial.population} designs x "
         f"{getattr(trial, 'stopped_at', None) or trial.generations} generations"
         + (f" (stopped early: no better design for {trial.patience})" if getattr(trial, "stopped_at", None) else "")
         + ", "
         f"seed {trial.seed}; {len(uniq)} distinct designs evaluated ({len(feasible)} feasible), "
         f"{secs / 60:.0f} CPU-minutes. Each design runs the full `eox calc` checks and the terrain course "
         f"({', '.join(trial.course_configs) or 'no course runs'})."
         + (" Fixed for every design: " + ", ".join(f"`{k}` = {v}" for k, v in trial.overrides.items()) + "."
            if trial.overrides else ""), ""]

    L += ["## Answer: the best design against today's", "",
          "| Metric | Today | Best | |", "|---|---|---|---|"]
    if "error" in top:
        L += ["", f"No design could be evaluated: {top['error']}"]
        return "\n".join(L) + "\n"
    for m in SHOWN:
        a, b = reference.get("metrics", {}).get(m), top["metrics"][m]
        unit, desc = METRICS[m]
        L.append(f"| {desc} | {_fmt(a)} | **{_fmt(b)}** | {unit} |")
    v_ref, v_top = violation(trial, reference), violation(trial, top)
    L += ["", f"**Score** (lower is better): today {score(trial, reference):.2f}"
          + (" (breaks a constraint)" if v_ref else "") + f"; best {score(trial, top):.2f}"
          + (" (breaks a constraint: no feasible design found)" if v_top else "") + ".", ""]
    L += ["| Gene | Why | Range | Today | Best |", "|---|---|---|---|---|"]
    edges = []
    for g in trial.genes:
        rng = " / ".join(_fmt(c) for c in g.choices) if g.choices is not None else f"{_fmt(g.lo)} to {_fmt(g.hi)}"
        v = top["genes"][g.key]
        edge = g.choices is None and (abs(v - g.lo) <= (g.step or 0) or abs(v - g.hi) <= (g.step or 0))
        edges += [g.key] if edge else []
        L.append(f"| `{g.key}` | {g.why} | {rng} | {_fmt(reference['genes'][g.key])} | **{_fmt(v)}**"
                 + (" (range limit)" if edge else "") + " |")
    L += [""]
    if edges:
        L += [f"At a range limit: {', '.join(f'`{k}`' for k in edges)}. The best value may lie beyond it; "
              "widen the range if the design allows, or treat the limit as a real constraint.", ""]
    if top.get("fails"):
        L += ["The best design still fails: " + "; ".join(top["fails"]) + ".", ""]
    if top.get("warns"):
        L += ["Course warnings on the best design: " + "; ".join(top["warns"]) + ".", ""]
    if reference.get("fails"):
        L += ["Today's design, scored by this trial, fails: " + "; ".join(reference["fails"]) + ".", ""]

    L += ["## Leaderboard", "", "| # | Score | " + " | ".join(f"`{g.key.split('.', 1)[1]}`" for g in trial.genes)
          + " | Grip | Working slope | Course WARN | Mass |",
          "|---" * (len(trial.genes) + 6) + "|"]
    for i, r in enumerate(sorted(feasible, key=lambda r: rank_key(trial, r))[:10], 1):
        m = r["metrics"]
        L.append(f"| {i} | {score(trial, r):.2f} | " + " | ".join(_fmt(r["genes"][g.key]) for g in trial.genes)
                 + f" | {m['grip_limit_deg']:g} | {m['working_slope_deg']:g} | {m['course_warns']:g} | {m['mass_kg']:.0f} |")
    if not feasible:
        L.append("| | no feasible design | |")
    L += ["", "## Progress", "",
          "<picture>",
          f'  <source media="(prefers-color-scheme: dark)" srcset="progress-dark.svg">',
          f'  <img alt="Score of every design by generation, and the best so far" src="progress-light.svg" width="100%">',
          "</picture>", "",
          "## Adopting", "",
          f"`best.toml` lists the best design's changed values as `[overrides]` for `design/models/{trial.model}.toml`. "
          "A trial is evidence for a decision, not the decision: review the numbers above, then edit the model "
          "file in a pull request, so the change and its reasons are recorded.", "",
          "Objectives and constraints:", ""]
    for o in trial.objectives:
        L.append(f"- {o.goal} `{o.metric}` ({METRICS[o.metric][1]}), weight {o.weight:g} per {o.scale:g} {METRICS[o.metric][0]}"
                 + (f", no extra credit past {o.cap:g}" if o.cap is not None else ""))
    for c in trial.constraints:
        lim = " and ".join(x for x in (f">= {c.min:g}" if c.min is not None else "", f"<= {c.max:g}" if c.max is not None else "") if x)
        L.append(f"- constraint: `{c.metric}` {lim}")
    return "\n".join(L) + "\n"


def progress_svg(trial: Trial, individuals: list[dict], reference: dict, theme: str) -> str:
    """Score by generation: every design (hollow = breaks a constraint), the
    best feasible so far, and today's design as a reference line."""
    t = THEMES[theme]
    W, H = 760, 380
    x0, x1, y0, y1 = 70, W - 30, 90, H - 50
    recs = [r for r in individuals if score(trial, r) != float("inf")]
    vals = [score(trial, r) for r in recs] + ([score(trial, reference)] if "error" not in reference else [])
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or 1.0
    lo, hi = lo - pad, hi + pad
    G = max((r.get("generation", 0) for r in individuals), default=0) + 1
    X = lambda g: x0 + (x1 - x0) * (g / max(1, G - 1))          # noqa: E731
    Y = lambda v: y0 + (y1 - y0) * (v - lo) / (hi - lo)          # noqa: E731  lower score = better = higher up
    s = Svg(W, H, theme)
    s.text(16, 26, f"Trial {trial.name}: score by generation", 16, weight=600)
    s.text(16, 44, "lower score is better and plots higher · each dot is one design · hollow = breaks a constraint",
           11, t["ink2"])
    items = [("design", t["series"][0]), ("best so far", t["series"][1]), ("today's design", t["muted"])]
    lx = 16
    for label, col in items:
        if label == "design":
            s.add(f'<circle cx="{lx + 6}" cy="64" r="4" fill="{col}"/>')
        else:
            s.line(lx, 64, lx + 14, 64, col, 2, dash="4 3" if label.startswith("today") else None)
        s.text(lx + 20, 68, label, 11, t["ink2"])
        lx += 30 + 6.5 * len(label)
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        s.line(x0, Y(v), x1, Y(v), t["grid"], 1)
        s.text(x0 - 8, Y(v) + 4, f"{v:.1f}", 10, t["muted"], "end")
    for g in range(G):
        s.text(X(g), y1 + 18, g + 1, 10, t["muted"], "middle")
    s.text((x0 + x1) / 2, y1 + 36, "generation", 11, t["ink2"], "middle")
    if "error" not in reference:
        s.line(x0, Y(score(trial, reference)), x1, Y(score(trial, reference)), t["muted"], 1.5, dash="4 3")
    best_so_far, pts = float("inf"), []
    for g in range(G):
        gen = [r for r in recs if r.get("generation") == g]
        for i, r in enumerate(gen):
            jitter = (i - len(gen) / 2) * 1.6
            ok = violation(trial, r) == 0
            fill = t["series"][0] if ok else "none"
            s.add(f'<circle cx="{X(g) + jitter:.1f}" cy="{Y(score(trial, r)):.1f}" r="4" fill="{fill}" '
                  f'stroke="{t["series"][0] if not ok else t["surface"]}" stroke-width="{1.2 if not ok else 1}"/>')
            if ok:
                best_so_far = min(best_so_far, score(trial, r))
        if best_so_far < float("inf"):
            pts.append(f"{X(g):.1f},{Y(best_so_far):.1f}")
    if pts:
        s.add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{t["series"][1]}" stroke-width="2"/>')
    return s.render(f"Trial {trial.name} progress", "Score of every design per generation, the best feasible score "
                    "so far, and today's design as a dashed reference line.")


def write(trial: Trial, individuals: list[dict], reference: dict) -> list:
    out = trial.out
    out.mkdir(parents=True, exist_ok=True)
    top = best(trial, individuals)
    files = [out / "report.md", out / "best.toml", out / "progress-light.svg", out / "progress-dark.svg"]
    files[0].write_text(markdown(trial, individuals, reference))
    files[1].write_text(best_toml(trial, top, reference) if "error" not in top else "# no design could be evaluated\n")
    for f, th in zip(files[2:], THEMES):
        f.write_text(progress_svg(trial, individuals, reference, th))
    return files
