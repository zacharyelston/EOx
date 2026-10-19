"""Bill of materials: fabricated parts from the layout + purchased parts CSV."""

from __future__ import annotations

import csv

from eox.params import ROOT
from eox.powerbox import Layout
from eox.sheetmetal import IN

PURCHASED = ROOT / "bom" / "powerbox-purchased.csv"
FIELDS = ["id", "category", "item", "spec", "qty", "est_unit_usd", "est_mass_kg_each",
          "examples_to_evaluate", "notes"]


def fabricated(lay: Layout) -> list[dict]:
    rows = []
    for part in lay.parts:
        qty = sum(1 for pl in lay.placed if pl.part is part)
        fx, fy = part.flat_bbox()
        bends = len(part.flanges)
        rows.append({
            "id": part.part_no,
            "category": "Sheet metal (SendCutSend)",
            "item": part.name,
            "spec": (f'{part.g.material} {part.g.t / IN:.3f}" | flat {fx:.0f} x {fy:.0f} mm | '
                     f'{bends} bend{"s" if bends != 1 else ""}' if bends else
                     f'{part.g.material} {part.g.t / IN:.3f}" | {fx:.0f} x {fy:.0f} mm | laser only'),
            "qty": qty,
            "est_unit_usd": "",          # get a live SCS quote: upload out/cad/<part>.step
            "est_mass_kg_each": round(part.mass_kg(), 3),
            "examples_to_evaluate": "",
            "notes": part.note,
        })
    return rows


def purchased() -> list[dict]:
    with open(PURCHASED, newline="") as f:
        return list(csv.DictReader(f))


def rollup(lay: Layout) -> tuple[list[dict], dict]:
    rows = fabricated(lay) + purchased()
    cost = sum(float(r["est_unit_usd"] or 0) * float(r["qty"]) for r in rows)
    mass = sum(float(r["est_mass_kg_each"] or 0) * float(r["qty"]) for r in rows)
    return rows, {"purchased_usd": cost, "mass_kg": mass,
                  "sheet_parts": sum(int(r["qty"]) for r in rows if r["id"].startswith("PB-"))}


def write(rows: list[dict], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
