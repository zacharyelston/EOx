"""Baseline: EOX models side by side with real machines on the same checks
and the same terrain course (`uv run eox baseline`)."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from datetime import date

from eox.params import ROOT

MODELS = ("home", "pro")


def _eox(model: str) -> dict:
    from eox import bom, calcs, tractor
    from eox.calcs.drive import grip_limit
    from eox.calcs.vehicle import stability
    from eox.params import load
    from eox.sim import run as sim
    from eox.tractor import DECK

    p = load(model)
    tr = tractor.build(p)
    v = p.vehicle
    angles = [0.0] + ([p.layout.articulation_max_deg] if tr.articulated else [])
    worst = min(x for g in angles for x in stability(tr, g, DECK).values())      # mowing: deck fitted, like the references
    _, tot = bom.rollup(p, tr.box)
    rep = calcs.run(p, tr)
    runtime = next(c.value for c in rep.checks if c.group == "Mode mowing" and c.name.startswith("runtime"))
    m = {"mass_kg": tr.mass(fitted=DECK) - v.mass_operator_kg - v.mass_payload_kg, "runtime_h": float(runtime),
         "cross_slope_deg": float(getattr(v, "max_cross_slope_deg", v.max_slope_deg)),
         "working_slope_deg": worst / 2, "grip_limit_deg": grip_limit(p, tr, DECK),
         "rated_slope_deg": float(v.max_slope_deg), "cost_usd": tot["total"]["usd"],
         "front_share_pct": 100 * tr.axle_loads_n(fitted=DECK)["front"] / (tr.mass(fitted=DECK) * 9.81)}
    r = sim.run(p, tr, DECK, keep_trajectory=False)
    kind = "EOX, electric, articulated AWD" if tr.articulated else "EOX, electric, 2WD"
    return {"name": p.model.name, "kind": kind, "metrics": m, "run": _slim(r), "source": f"design/models/{model}.toml"}


def _ref(name: str) -> dict:
    from eox import reference
    out = reference.evaluate(name)
    p, v = out["p"], out["p"].vehicle
    out["metrics"]["runtime_h"] = getattr(p.spec, "runtime_h", None)
    out["metrics"]["cross_slope_deg"] = float(getattr(v, "max_cross_slope_deg", v.max_slope_deg))
    return {"name": out["name"], "kind": out["kind"], "metrics": out["metrics"], "run": _slim(out["runs"][0]),
            "source": f"design/reference/{name}.toml"}


def _slim(r):
    """What the report needs from a run, without the trajectory (cheap to pass between processes)."""
    r.times = r.qpos = None
    for o in r.obstacles:
        o.snapshot = None
    return r


def _job(arg):
    kind, name = arg
    return _eox(name) if kind == "eox" else _ref(name)


def run(workers: int | None = None) -> list[dict]:
    from eox import reference
    jobs = [("eox", m) for m in MODELS] + [("ref", n) for n in reference.NAMES]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_job, jobs))


def markdown(rows: list[dict], course) -> str:
    from eox.sim.report import counts, headline

    L = ["# Baselines: EOX against real machines", "",
         f"Generated {date.today().isoformat()} by `uv run eox baseline`. Every machine runs the same static "
         f"checks (tip angle, grip) and the same terrain course ({course.length:.0f} m, "
         f"{len(course.segments)} obstacles, deck fitted, turf). Real machines are modelled from their published "
         "specs in `design/reference/`; what the makers don't publish (weight split, CG height) is estimated "
         "and marked REF there. Each machine is scored against its own rated slope.", "",
         "| Machine | Type | Mass (kg) | Price ($) | Rated climb / across | Grip limit | Working slope | Front axle share (with operator) | Mowing runtime | Course |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        m, c = r["metrics"], counts(r["run"])
        rt = f"{m['runtime_h']:.1f} h" if m.get("runtime_h") else "gas"
        L.append(f"| {r['name']} | {r['kind']} | {m['mass_kg']:.0f} | {m['cost_usd']:,.0f} | "
                 f"{m['rated_slope_deg']:g} / {m['cross_slope_deg']:g} deg | "
                 f"{m['grip_limit_deg']:.1f} deg | {m['working_slope_deg']:.1f} deg | {m['front_share_pct']:.0f} % | {rt} | "
                 f"{c['FAIL']} FAIL, {c['WARN']} WARN, {c['PASS']} PASS" + (f", {c['INFO']} INFO" if c["INFO"] else "") + " |")
    L += ["", "Mass is with the deck, without the operator. Price: EOX = purchased parts (budgetary); real machines = "
          "list price when checked. Grip limit: the steepest climb the driven tyres hold on turf (traction 0.5), "
          "deck fitted, as `eox calc` computes it. Working slope: half the lowest static tip angle, deck fitted "
          "(`eox calc` also checks EOX without its deck, which can be lower).", "",
          "## Course, obstacle by obstacle", "",
          "| Machine | " + " | ".join(s.name for s in course.segments) + " |",
          "|---" * (len(course.segments) + 1) + "|"]
    for r in rows:
        L.append(f"| {r['name']} | " + " | ".join(f"{o.status}: {headline(o)}" for o in r["run"].obstacles) + " |")
    L += ["", "Sources: each machine's file in `design/reference/` lists where every published number comes from.", ""]
    return "\n".join(L) + "\n"


def svg(rows: list[dict], course, theme: str) -> str:
    """Machines x obstacles: a status chip (icon + label) per cell."""
    from eox.drawings import STATUS, THEMES, Svg

    t = THEMES[theme]
    n = len(course.segments)
    name_w, col_w, row_h, top = 210, 104, 34, 92
    W = name_w + n * col_w + 32
    s = Svg(W, top + row_h * len(rows) + 40, theme)
    s.text(16, 26, "EOX and real machines on the same terrain course", 16, weight=600)
    s.text(16, 44, "deck fitted, turf, 3 km/h · each machine scored against its own rated slope (INFO = steeper "
           "than its rating) · details: docs/baselines.md", 11, t["ink2"])
    for i, seg in enumerate(course.segments):
        s.text(name_w + (i + 0.5) * col_w, top - 14, seg.name, 11, t["ink"], "middle", weight=600)
    s.line(16, top - 6, W - 16, top - 6, t["base"], 1)
    for k, r in enumerate(rows):
        y = top + k * row_h
        if k:
            s.line(16, y, W - 16, y, t["grid"], 1)
        s.text(16, y + 21, r["name"], 12, t["ink"], weight=600 if r["name"].startswith("EOX") else 400)
        for i, o in enumerate(r["run"].obstacles):
            cx = name_w + i * col_w + 18
            colour, glyph = STATUS[o.status]
            s.add(f'<circle cx="{cx:.1f}" cy="{y + 17:.1f}" r="7" fill="{colour or t["muted"]}"/>')
            s.text(cx, y + 21, glyph, 10, "#0b0b0b" if o.status == "WARN" else "#ffffff", "middle", weight=700)
            s.text(cx + 12, y + 21, o.status, 11, t["ink"])
    return s.render("EOX and real machines on the terrain course",
                    "Status of each machine on each obstacle: " +
                    "; ".join(f"{r['name']}: " + ", ".join(f"{o.name} {o.status}" for o in r["run"].obstacles) for r in rows))


def write(rows: list[dict]) -> list:
    from eox.drawings import THEMES
    from eox.params import load
    from eox.sim import terrain

    course = terrain.build(load("home").course)
    out = [ROOT / "docs" / "baselines.md"] + [ROOT / "docs" / "img" / f"baselines-{th}.svg" for th in THEMES]
    out[0].write_text(markdown(rows, course))
    for f, th in zip(out[1:], THEMES):
        f.write_text(svg(rows, course, th))
    return out
