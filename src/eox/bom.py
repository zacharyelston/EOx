"""Bill of materials for a model: purchased parts (bom/purchased.csv, by
module) x the model's module counts, plus the power box's fabricated parts."""

from __future__ import annotations

import csv

from eox.params import ROOT
from eox.powerbox import Layout
from eox.sheetmetal import IN

PURCHASED = ROOT / "bom" / "purchased.csv"
FIELDS = ["module", "id", "category", "item", "spec", "qty", "modules", "qty_total", "est_unit_usd",
          "est_mass_kg_each", "examples_to_evaluate", "notes"]


def fabricated(box: Layout) -> list[dict]:
    rows = []
    for part in box.parts:
        qty = sum(1 for pl in box.placed if pl.part is part)
        fx, fy = part.flat_bbox()
        bends = len(part.flanges)
        how = f'flat {fx:.0f} x {fy:.0f} mm | {bends} bend{"s" if bends != 1 else ""}' if bends else f"{fx:.0f} x {fy:.0f} mm | laser only"
        rows.append({
            "module": "powerbox", "id": part.part_no, "category": "Sheet metal (SendCutSend)", "item": part.name,
            "spec": f'{part.g.material} {part.g.t / IN:.3f}" | {how}', "qty": qty,
            "est_unit_usd": "",          # get a live SCS quote: upload out/cad/<part>.step
            "est_mass_kg_each": round(part.mass_kg(), 3), "examples_to_evaluate": "", "notes": part.note,
        })
    return rows


def purchased() -> list[dict]:
    with open(PURCHASED, newline="") as f:
        return list(csv.DictReader(f))


def rollup(p, box: Layout) -> tuple[list[dict], dict]:
    counts = vars(p.bom)
    rows = []
    for row in fabricated(box) + purchased():
        n = counts.get(row["module"], 0)
        if not n:
            continue
        row = dict(row, modules=n, qty_total=int(float(row["qty"])) * n)
        rows.append(row)
    by_module: dict[str, dict] = {}
    for row in rows:
        m = by_module.setdefault(row["module"], {"usd": 0.0, "kg": 0.0, "quote": 0})
        m["usd"] += float(row["est_unit_usd"] or 0) * row["qty_total"]
        m["kg"] += float(row["est_mass_kg_each"] or 0) * row["qty_total"]
        m["quote"] += 0 if row["est_unit_usd"] else row["qty_total"]
    total = {"usd": sum(m["usd"] for m in by_module.values()), "kg": sum(m["kg"] for m in by_module.values()),
             "quote": sum(m["quote"] for m in by_module.values())}
    return rows, {"modules": by_module, "total": total}


def write(rows: list[dict], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
