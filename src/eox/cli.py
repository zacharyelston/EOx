"""`uv run eox calc | build | bom | all`"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from eox import bom, calcs, powerbox
from eox.params import OUT, load

COLS = ("status", "group", "check", "value", "limit", "note")


def _table(rows: list[tuple[str, ...]]) -> str:
    rows = [COLS] + rows
    widths = [min(max(len(r[i]) for r in rows), cap) for i, cap in enumerate((6, 14, 58, 16, 12, 70))]
    out = []
    for n, r in enumerate(rows):
        out.append("  ".join(c[:w].ljust(w) for c, w in zip(r, widths)).rstrip())
        if n == 0:
            out.append("  ".join("-" * w for w in widths))
    return "\n".join(out)


def cmd_calc(p, lay, args) -> int:
    rep = calcs.run(p, lay)
    shown = [c for c in rep.checks if args.all or not c.group.startswith("SCS ") or c.status != "PASS"]
    print(_table([c.row() for c in shown]))
    counts = {s: sum(c.status == s for c in rep.checks) for s in ("FAIL", "WARN", "PASS", "INFO")}
    hidden = len(rep.checks) - len(shown)
    print(f"\n{counts['FAIL']} FAIL  {counts['WARN']} WARN  {counts['PASS']} PASS  {counts['INFO']} INFO"
          + (f"  ({hidden} passing SCS checks hidden; --all shows them)" if hidden else ""))
    path = OUT / "powerbox-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_markdown(p, lay, rep, counts))
    print(f"report: {path.relative_to(OUT.parent)}")
    return 1 if counts["FAIL"] else 0


def _markdown(p, lay, rep, counts) -> str:
    lines = [f"# Power box check report — rev {p.meta.revision}", "",
             f"Generated {date.today().isoformat()} from `design/powerbox.toml` by `uv run eox calc`. "
             "Screening-level hand calcs; see `src/eox/calcs.py` for each model.", "",
             f"**Box (outer):** {lay.part('PB-102').A:.0f} x {lay.part('PB-102').B:.0f}"
             f" x {lay.H_out:.0f} mm (L x W x H, cover included)  ",
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


def cmd_build(p, lay, args) -> int:
    from build123d import Compound, export_step, export_stl

    cad = OUT / "cad"
    for part in lay.parts:
        files = part.export(cad)
        print(f"{part.part_no}  {part.name:<24} {files['step'].split('/')[-1]}  {files['dxf'].split('/')[-1]}")
    items = powerbox.assembly(lay)
    asm = Compound(children=[s for _, s in items])
    export_step(asm, str(cad / "powerbox-assembly.step"))
    stl = cad / "stl"
    stl.mkdir(exist_ok=True)
    for kind, s in items:
        export_stl(s, str(stl / f"{kind}__{s.label}.stl"), tolerance=0.2, angular_tolerance=0.3)
    print(f"assembly: {(cad / 'powerbox-assembly.step').relative_to(OUT.parent)}  + preview STLs in {stl.relative_to(OUT.parent)}")
    return 0


def cmd_bom(p, lay, args) -> int:
    rows, tot = bom.rollup(lay)
    path = OUT / "powerbox-bom.csv"
    bom.write(rows, path)
    w = max(len(r["item"]) for r in rows)
    for r in rows:
        cost = f'${float(r["est_unit_usd"]) * float(r["qty"]):>7,.0f}' if r["est_unit_usd"] else "   quote"
        print(f'{r["id"]:<7} {r["item"]:<{w}}  x{r["qty"]:<3} {cost}')
    print(f"\npurchased parts ~${tot['purchased_usd']:,.0f} (budgetary) + SendCutSend quote for "
          f"{tot['sheet_parts']} sheet parts; mass ~{tot['mass_kg']:.1f} kg")
    print(f"bom: {path.relative_to(OUT.parent)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eox", description="EOX power box: calcs, CAD, BOM")
    ap.add_argument("command", choices=["calc", "build", "bom", "all"])
    ap.add_argument("--all", action="store_true", help="calc: also list passing SCS checks")
    args = ap.parse_args(argv)
    p = load()
    lay = powerbox.build(p)
    cmds = {"calc": [cmd_calc], "build": [cmd_build], "bom": [cmd_bom], "all": [cmd_calc, cmd_bom, cmd_build]}
    rc = 0
    for fn in cmds[args.command]:
        rc |= fn(p, lay, args)
        print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
