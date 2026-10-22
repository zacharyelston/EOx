"""Tyre-pressure sweep (`uv run eox tyres --model home`): grip, rolling
resistance and the terrain course's climbs across drive-tyre pressures, on
firm, typical and wet lawn."""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from datetime import date

from eox.params import ROOT

PSI = 6.895
PRESSURES_PSI = (8, 10, 12, 14, 17, 20)
GROUNDS = (("firm dry lawn", 1000), ("lawn turf", 400), ("soft wet lawn", 200))


def _point(args) -> dict:
    model, psi, ground, ci, course = args
    from eox import tractor
    from eox.calcs.drive import grip_limit
    from eox.params import load
    from eox.sim import run as sim
    from eox.tractor import DECK

    p = load(model, {"axle.tire_pressure_kpa": round(psi * PSI, 1), "ground.cone_index_kpa": ci})
    tr = tractor.build(p)
    drive = next(ax.name for ax in tr.axles if ax.driven)
    t = tr.tyres[drive]
    out = {"model": model, "psi": psi, "ground": ground, "ci": ci, "grip_limit": grip_limit(p, tr, DECK),
           "grip": t["grip"], "rolling": p.vehicle.rolling_resistance, "deflection_ratio": t["deflection_ratio"],
           "deflection_mm": t["deflection_mm"]}
    if course:
        r = sim.run(p, tr, DECK, keep_trajectory=False)
        out["climbs"] = {o.name: (o.outcome, round(o.at_peak_s, 1), round(o.max_slip)) for o in r.obstacles if o.kind == "ramp"}
        out["energy_wh"] = r.energy_wh
        out["warns"] = sum(o.status == "WARN" for o in r.obstacles)
    return out


def run(model: str, course: bool = True, workers: int | None = None) -> list[dict]:
    jobs = [(model, psi, g, ci, course and g == "lawn turf") for g, ci in GROUNDS for psi in PRESSURES_PSI]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_point, jobs))


def min_safe_psi(model: str) -> float:
    """Lowest drive-tyre pressure that keeps deflection within the ground file's limit."""
    from eox import tractor, tyres
    from eox.params import load
    p = load(model)
    tr = tractor.build(p)
    ax = next(a for a in tr.axles if a.driven)
    t = tr.tyres[ax.name]
    h, W = t["tyre"].section_height / 1000, t["load_n"]
    k_needed = W / (p.ground.max_deflection_ratio * h)
    p_kpa = k_needed / (math.pi * math.sqrt(t["tyre"].diameter / 1000 * t["tyre"].width / 1000)) / 1000 - p.ground.carcass_kpa
    return p_kpa / PSI


def markdown(model: str, rows: list[dict], design_psi: float, floor_psi: float) -> str:
    L = [f"# Tyre-pressure sweep: EOX {model.capitalize()}", "",
         f"Generated {date.today().isoformat()} by `uv run eox tyres --model {model}`. Drive-tyre pressure varied, "
         f"deck fitted; everything else as designed (drive tyres {design_psi:.0f} psi). Grip and rolling "
         "resistance from tyre size, pressure, load and ground strength (`src/eox/tyres.py`, Brixius / ASAE D497). "
         f"Below about {floor_psi:.1f} psi the drive tyres deflect more than "
         "the ground file's limit at static load (sidewall overload).", "",
         "| Ground | psi | Deflection | Tyre grip | Rolling resistance | Climb grip limit |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['ground']} | {r['psi']} | {r['deflection_mm']:.0f} mm ({r['deflection_ratio'] * 100:.0f} %) | "
                 f"{r['grip']:.2f} | {r['rolling']:.3f} | {r['grip_limit']:.1f} deg |")
    course = [r for r in rows if "climbs" in r]
    if course:
        names = list(course[0]["climbs"])
        L += ["", "## On the course (lawn turf)", "",
              "| psi | " + " | ".join(names) + " | Course WARN | Drive energy |", "|---" * (len(names) + 3) + "|"]
        for r in course:
            cells = [f"{o} ({pk:g} s at peak, {sl}% slip)" if o == "cleared" else o for o, pk, sl in r["climbs"].values()]
            L.append(f"| {r['psi']} | " + " | ".join(cells) + f" | {r['warns']} | {r['energy_wh']:.1f} Wh |")
    return "\n".join(L) + "\n"


def svg(model: str, rows: list[dict], design_psi: float, floor_psi: float, theme: str, rated: float = 0.0) -> str:
    """Climb grip limit vs drive-tyre pressure, one line per ground."""
    from eox.drawings import THEMES, Svg

    t = THEMES[theme]
    W, H = 760, 400
    x0, x1, y0, y1 = 70, W - 150, 80, H - 56
    ps = [p for p in PRESSURES_PSI]
    lo_p, hi_p = min(ps) - 1, max(ps) + 1
    vals = [r["grip_limit"] for r in rows] + ([rated] if rated else [])
    lo_v, hi_v = math.floor(min(vals) - 1), math.ceil(max(vals) + 1)
    X = lambda v: x0 + (x1 - x0) * (v - lo_p) / (hi_p - lo_p)      # noqa: E731
    Y = lambda v: y1 - (y1 - y0) * (v - lo_v) / (hi_v - lo_v)      # noqa: E731
    s = Svg(W, H, theme)
    s.text(16, 26, f"EOX {model.capitalize()}: steepest climb on grip vs drive-tyre pressure", 16, weight=600)
    shaded = floor_psi > lo_p
    s.text(16, 44, "deck fitted · each line is a ground · dashed: design pressure and rated climb"
           + (" · shaded: tyres overloaded" if shaded else f" · tyres overload below {floor_psi:.1f} psi"), 11, t["ink2"])
    if floor_psi > lo_p:
        s.add(f'<rect x="{X(lo_p):.1f}" y="{y0}" width="{X(min(floor_psi, hi_p)) - X(lo_p):.1f}" height="{y1 - y0}" '
              f'fill="{t["grid"]}" opacity="0.7"/>')
    for v in range(lo_v, hi_v + 1, max(1, (hi_v - lo_v) // 6)):
        s.line(x0, Y(v), x1, Y(v), t["grid"], 1)
        s.text(x0 - 8, Y(v) + 4, f"{v}°", 10, t["muted"], "end")
    for p_ in ps:
        s.text(X(p_), y1 + 18, f"{p_}", 10, t["muted"], "middle")
    s.text((x0 + x1) / 2, y1 + 36, "drive-tyre pressure (psi)", 11, t["ink2"], "middle")
    s.line(X(design_psi), y0, X(design_psi), y1, t["muted"], 1.2, dash="4 3")
    if rated:
        s.line(x0, Y(rated), x1, Y(rated), t["muted"], 1.2, dash="4 3")
        s.text(x1 + 10, Y(rated) + 4, f"rated climb {rated:g}°", 11, t["ink2"])
    for i, (g, _) in enumerate(GROUNDS):
        pts = sorted((r["psi"], r["grip_limit"]) for r in rows if r["ground"] == g)
        col = t["series"][i]
        s.add(f'<polyline points="{" ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in pts)}" fill="none" stroke="{col}" '
              f'stroke-width="2" stroke-linejoin="round"/>')
        for a, b in pts:
            s.add(f'<circle cx="{X(a):.1f}" cy="{Y(b):.1f}" r="4" fill="{col}" stroke="{t["surface"]}" stroke-width="2"/>')
        a, b = pts[-1]
        s.text(X(a) + 10, Y(b) + 4, g, 11, t["ink"])
    return s.render(f"EOX {model} tyre-pressure sweep",
                    "Steepest climb on grip versus drive-tyre pressure for " + ", ".join(g for g, _ in GROUNDS) + ": " +
                    "; ".join(f"{r['ground']} {r['psi']} psi {r['grip_limit']:.1f} deg" for r in rows))


def write(model: str, rows: list[dict]) -> list:
    from eox.drawings import THEMES
    from eox.params import OUT, load

    design_psi = load(model).axle.tire_pressure_kpa / PSI
    floor_psi = min_safe_psi(model)
    out = [OUT / f"{model}-tyres.md"] + [ROOT / "docs" / "img" / f"{model}-tyres-{th}.svg" for th in THEMES]
    out[0].write_text(markdown(model, rows, design_psi, floor_psi))
    for f, th in zip(out[1:], THEMES):
        f.write_text(svg(model, rows, design_psi, floor_psi, th, load(model).vehicle.max_slope_deg))
    return out
