"""`uv run eox calc | build | bom | drawings | all [--model pro]`"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from pathlib import Path

from eox import bom, calcs, drawings, powerbox, tractor
from eox.params import MODELS, OUT, ROOT, load

COLS = ("status", "group", "check", "value", "limit", "note")


def _table(rows: list[tuple[str, ...]]) -> str:
    rows = [COLS] + rows
    widths = [min(max(len(r[i]) for r in rows), cap) for i, cap in enumerate((6, 18, 60, 22, 22, 70))]
    out = []
    for n, r in enumerate(rows):
        out.append("  ".join(c[:w].ljust(w) for c, w in zip(r, widths)).rstrip())
        if n == 0:
            out.append("  ".join("-" * w for w in widths))
    return "\n".join(out)


def cmd_calc(p, tr, args) -> int:
    rep = calcs.run(p, tr)
    shown = [c for c in rep.checks if args.all or not c.group.startswith("SCS ") or c.status != "PASS"]
    print(_table([c.row() for c in shown]))
    counts = {s: sum(c.status == s for c in rep.checks) for s in ("FAIL", "WARN", "PASS", "INFO")}
    hidden = len(rep.checks) - len(shown)
    print(f"\n{p.model.name}: {counts['FAIL']} FAIL  {counts['WARN']} WARN  {counts['PASS']} PASS  {counts['INFO']} INFO"
          + (f"  ({hidden} passing SCS checks hidden; --all shows them)" if hidden else ""))
    path = OUT / f"{args.model}-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_markdown(p, tr, rep, counts))
    print(f"report: {path.relative_to(OUT.parent)}")
    return 1 if counts["FAIL"] else 0


def _markdown(p, tr, rep, counts) -> str:
    L, W, H = tr.box.outer
    lines = [f"# {p.model.name} check report: model rev {p.model.revision}, power box rev {p.meta.revision}", "",
             f"Generated {date.today().isoformat()} by `uv run eox calc --model {p.model.name.split()[-1].lower()}` "
             "from the files in `design/`. Screening-level hand calcs; each model is documented in `src/eox/calcs/`.", "",
             f"**Machine:** {tr.mass() - p.vehicle.mass_operator_kg - p.vehicle.mass_payload_kg:.0f} kg without operator  ",
             f"**Power box (outer):** {L:.0f} x {W:.0f} x {H:.0f} mm  ",
             f"**Result:** {counts['FAIL']} FAIL, {counts['WARN']} WARN, {counts['PASS']} PASS", ""]
    group = None
    for c in rep.checks:
        if c.group != group:
            group = c.group
            lines += ["", f"## {group}", "", "| | Check | Value | Limit | Note |", "|---|---|---|---|---|"]
        s, _, name, val, lim, note = c.row()
        badge = {"FAIL": "**FAIL**", "WARN": "WARN", "PASS": "pass", "INFO": "info"}[s]
        lines.append(f"| {badge} | {name} | {val} | {lim} | {note} |")
    return "\n".join(lines) + "\n"


def _export_scene(items, folder, step_name):
    from build123d import Compound, export_step, export_stl

    folder.mkdir(parents=True, exist_ok=True)
    export_step(Compound(children=[s for _, s in items]), str(folder / step_name))
    stl = folder / "stl"
    stl.mkdir(exist_ok=True)
    for old in stl.glob("*.stl"):
        old.unlink()
    for kind, s in items:
        export_stl(s, str(stl / f"{kind}__{s.label}.stl"), tolerance=0.3, angular_tolerance=0.3)
    return stl


def cmd_build(p, tr, args) -> int:
    cad = OUT / "cad" / "powerbox"
    for part in tr.box.parts:
        files = part.export(cad)
        print(f"{part.part_no}  {part.name:<24} {files['step'].split('/')[-1]}  {files['dxf'].split('/')[-1]}")
    stl = _export_scene(powerbox.assembly(tr.box), cad, "powerbox-assembly.step")
    print(f"power box assembly + preview STLs: {stl.parent.relative_to(OUT.parent)}")
    stl = _export_scene(tr.assembly(), OUT / "cad" / args.model, f"{args.model}-layout.step")
    print(f"{p.model.name} layout + preview STLs: {stl.parent.relative_to(OUT.parent)}")
    if p.model.layout == "articulated":
        gamma = p.layout.articulation_max_deg
        stl = _export_scene(tr.assembly(gamma), OUT / "cad" / f"{args.model}-articulated",
                            f"{args.model}-articulated.step")
        print(f"{p.model.name} at full lock ({gamma:g} deg): {stl.parent.relative_to(OUT.parent)}")
    return 0


def cmd_drawings(p, tr, args) -> int:
    paths = drawings.write_all(p, tr, args.out)
    print(f"{len(paths)} figures (light + dark) in {args.out}")
    return 0


def cmd_bom(p, tr, args) -> int:
    rows, tot = bom.rollup(p, tr.box)
    path = OUT / f"{args.model}-bom.csv"
    bom.write(rows, path)
    w = max(len(r["item"]) for r in rows)
    module = None
    for r in rows:
        if r["module"] != module:
            module = r["module"]
            m = tot["modules"][module]
            print(f"\n[{module}] x{r['modules']}   ~${m['usd']:,.0f}  {m['kg']:.0f} kg")
        cost = f'${float(r["est_unit_usd"]) * r["qty_total"]:>7,.0f}' if r["est_unit_usd"] else "   quote"
        print(f'  {r["id"]:<7} {r["item"]:<{w}}  x{r["qty_total"]:<3} {cost}')
    t = tot["total"]
    print(f"\n{p.model.name}: purchased parts ~${t['usd']:,.0f} (budgetary) + quotes for {t['quote']} fabricated "
          f"parts; parts mass ~{t['kg']:.0f} kg")
    print(f"bom: {path.relative_to(OUT.parent)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eox", description="EOX: calcs, CAD and BOM for a tractor model")
    ap.add_argument("command", choices=["calc", "build", "bom", "drawings", "all"])
    ap.add_argument("--model", default="pro", choices=MODELS, help="design/models/<model>.toml (default: pro)")
    ap.add_argument("--all", action="store_true", help="calc: also list passing SCS checks")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "img", help="drawings: output folder (default docs/img)")
    args = ap.parse_args(argv)
    p = load(args.model)
    tr = tractor.build(p)
    cmds = {"calc": [cmd_calc], "build": [cmd_build], "bom": [cmd_bom], "drawings": [cmd_drawings],
            "all": [cmd_calc, cmd_bom, cmd_build, cmd_drawings]}
    rc = 0
    for fn in cmds[args.command]:
        rc |= fn(p, tr, args)
        print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
