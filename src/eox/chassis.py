"""Preliminary steel rail study: `uv run python -m eox.chassis`.

Compare a folded lipped C rail with a bolted flat side cover. Elastic bending
uses the formed shell alone: cover composite action is not assumed. Full-span
continuity at segment joints IS assumed and must be proved separately.
No CAD, fabrication drawings, bolt sizing or safety certification is produced.
"""

from __future__ import annotations

import argparse
import csv
import math
import tomllib
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from eox.params import ROOT, gauge, load_materials
from eox.sheetmetal import IN


@dataclass(frozen=True)
class Section:
    depth: float
    width: float
    lip: float
    thickness: float

    def __post_init__(self):
        if not all(math.isfinite(x) and x > 0 for x in (self.depth, self.width, self.lip, self.thickness)):
            raise ValueError("section dimensions must be finite and positive")

    @property
    def shell_area(self) -> float:
        return self.thickness * (self.depth + 2 * self.width + 2 * self.lip)

    @property
    def cover_area(self) -> float:
        return self.thickness * (self.depth + 2 * self.lip)

    @property
    def shell_i(self) -> float:
        """I about the horizontal neutral axis, sum of five rectangular strips (mm^4)."""
        h, w, f, t = self.depth, self.width, self.lip, self.thickness
        return (t * h**3 / 12 + 2 * (w * t**3 / 12 + w * t * (h / 2)**2)
                + 2 * (t * f**3 / 12 + t * f * ((h + f) / 2)**2))

    @property
    def gross_assembled_i(self) -> float:
        """Ideal no-slip shell + cover value, for comparison only."""
        return self.shell_i + self.thickness * (self.depth + 2 * self.lip)**3 / 12

    @property
    def modulus(self) -> float:
        return self.shell_i / (self.depth / 2 + self.lip)


def sweep(config: dict, materials: dict | None = None) -> list[dict]:
    mats = materials if materials is not None else load_materials()
    p, search = config["study"], config["search"]
    mat, rules = mats["mild_steel"], mats["scs"]
    positive = ("frame_length_mm", "support_span_mm", "rail_count", "gross_vehicle_mass_kg",
                "vertical_load_factor", "yield_safety_factor", "screening_yield_mpa",
                "deflection_span_ratio", "max_part_length_mm")
    if any(not math.isfinite(p[k]) or p[k] <= 0 for k in positive):
        raise ValueError("study dimensions, loads and limits must be finite and positive")
    if int(p["rail_count"]) != p["rail_count"] or p["splice_allowance_kg_per_joint"] < 0:
        raise ValueError("rail count must be integral and splice allowance nonnegative")
    blank_limits = sorted(x * IN for x in rules["bend_flat_max_in"])
    force = p["gross_vehicle_mass_kg"] * 9.81 * p["vertical_load_factor"] / p["rail_count"]
    span = p["support_span_mm"]
    rows = []
    for tin, h, w, f in product(search["thickness_in"], search["web_depth_mm"],
                              search["rail_width_mm"], search["return_lip_mm"]):
        g = gauge(mats, "mild_steel", tin * IN)
        section = Section(h, w, f, g.t)
        max_length = min(p["max_part_length_mm"], g.max_bend_len, blank_limits[1])
        segments = math.ceil(p["frame_length_mm"] / max_length)
        length = p["frame_length_mm"] / segments
        # Conservative envelope allowance only, not a computed bend deduction or flat pattern.
        flat_bound = h + 2 * w + 2 * f + 8 * (g.r + g.t)
        stress = force * span / 4 / section.modulus
        deflection = force * span**3 / (48 * mat["E_mpa"] * section.shell_i)
        mass_per_m = (section.shell_area + section.cover_area) * mat["density"] * 1e-6
        mass = mass_per_m * p["frame_length_mm"] / 1000 * p["rail_count"]
        splice_mass = p["rail_count"] * (segments - 1) * p["splice_allowance_kg_per_joint"]
        reasons = []
        if h - 2 * g.t < rules["u_channel_base_to_flange"] * w:
            reasons.append("channel tooling clearance")
        if min(w, f) < g.min_flange:
            reasons.append("minimum flange")
        if flat_bound > blank_limits[0] or h + 2 * f > blank_limits[0]:
            reasons.append("blank width bound")
        if length > min(g.max_bend_len, blank_limits[1]):
            reasons.append("bend length")
        if stress > p["screening_yield_mpa"] / p["yield_safety_factor"]:
            reasons.append("gross elastic stress")
        if deflection > span / p["deflection_span_ratio"]:
            reasons.append("gross elastic deflection")
        rows.append({"depth_mm": h, "width_mm": w, "lip_mm": f, "thickness_mm": g.t,
                     "shell_i_mm4": section.shell_i, "ideal_assembled_i_mm4": section.gross_assembled_i,
                     "stress_mpa": stress, "deflection_mm": deflection, "rail_pair_kg": mass,
                     "splice_allowance_kg": splice_mass, "estimated_rail_kit_kg": mass + splice_mass,
                     "segments_per_rail": segments, "part_length_mm": length,
                     "flat_width_bound_mm": flat_bound, "formed_parts": p["rail_count"] * segments,
                     "cover_parts": p["rail_count"] * segments, "bends": 4 * p["rail_count"] * segments,
                     "screen_pass": not reasons, "reasons": "; ".join(reasons)})
    return sorted(rows, key=lambda r: (not r["screen_pass"], r["estimated_rail_kit_kg"], r["deflection_mm"]))


def concept_svg(row: dict) -> str:
    """Dimensioned section study, without fabrication details."""
    h, w, f = (row[k] for k in ("depth_mm", "width_mm", "lip_mm"))
    scale = min(2.1, 290 / (h + 2 * f))
    x, mid = 100, 270
    top, bottom = mid - h * scale / 2, mid + h * scale / 2
    end = x + w * scale
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="570" viewBox="0 0 1120 570">
<title>EOX Home: folded steel kit rail concept</title>
<desc>Cross section of a lipped C rail with outward lips and a removable flat side cover, plus a schematic modular ladder chassis. Concept only.</desc>
<rect width="1120" height="570" fill="#f5f4ef"/>
<g font-family="Arial,sans-serif" fill="#202b32">
<text x="36" y="42" font-size="25" font-weight="bold">EOX Home | steel kit structure</text>
<text x="36" y="70" font-size="15" fill="#9b3d27">CONCEPT STUDY — NOT FABRICATION OR ORDER FILES</text>
<text x="36" y="111" font-size="18" font-weight="bold">Rail cross section</text>
<path d="M {end} {top-f*scale} V {top} H {x} V {bottom} H {end} V {bottom+f*scale}"
 fill="none" stroke="#2c6577" stroke-width="8" stroke-linejoin="round"/>
<path d="M {end+22} {top-f*scale} V {bottom+f*scale}" stroke="#bb633e" stroke-width="7"/>
<path d="M {end-12} {top-f*scale/2} H {end+35} M {end-12} {bottom+f*scale/2} H {end+35}"
 stroke="#253038" stroke-width="5"/>
<text x="36" y="448" font-size="16">Web {h:g} · width {w:g} · lips {f:g} mm</text>
<text x="36" y="474" font-size="16">Steel {row['thickness_mm']:.2f} mm · four shop bends</text>
<text x="36" y="500" font-size="14">Blue: formed shell. Orange: bolted side cover.</text>
<text x="36" y="523" font-size="14">Fasteners sit outside the closed cavity.</text>
<text x="480" y="111" font-size="18" font-weight="bold">Modular ladder frame — schematic plan</text>
<g fill="#d5e0df" stroke="#2c6577" stroke-width="3">
<rect x="500" y="175" width="540" height="30"/><rect x="500" y="340" width="540" height="30"/>
<rect x="530" y="205" width="28" height="135"/><rect x="730" y="205" width="28" height="135"/>
<rect x="975" y="205" width="28" height="135"/>
</g>
<g stroke="#bb633e" stroke-width="8"><path d="M 675 174 V 207 M 855 174 V 207 M 675 338 V 372 M 855 338 V 372"/></g>
<rect x="575" y="220" width="135" height="105" rx="5" fill="#e8dfc8" stroke="#8c7950" stroke-width="2"/>
<text x="589" y="265" font-size="15">Low battery</text><text x="590" y="289" font-size="15">mounting bay</text>
<path d="M 990 150 V 395" stroke="#2c6577" stroke-width="13"/>
<circle cx="990" cy="273" r="12" fill="#bb633e"/>
<text x="480" y="419" font-size="15">Bolt-on crossmembers, axle cradle and bearing carriers.</text>
<text x="480" y="445" font-size="15">Segment joints require load-transfer and fatigue checks.</text>
<text x="480" y="471" font-size="15">Standard pins, shafts, bushes and bearings are purchased.</text>
<text x="480" y="511" font-size="16" font-weight="bold">Rail steel + splice allowance: {row['estimated_rail_kit_kg']:.1f} kg</text>
<text x="480" y="537" font-size="14">Excludes crossmembers, axle parts, mounts and most hardware.</text>
</g></svg>'''


def write(config: dict, rows: list[dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "sections.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    passing = [r for r in rows if r["screen_pass"]]
    p = config["study"]
    lines = ["# Home steel chassis: preliminary rail study", "",
             "**Concept only. These are neither fabrication files nor an orderable kit.**", "",
             f"Screened {len(rows)} sections; {len(passing)} meet the limited elastic and geometry screens.", "",
             "The family is a folded lipped C shell with outward returns and a flat bolted side cover. "
             "The returns make fasteners accessible outside the cavity. Four-bend tooling still needs shop review.", "",
             f"Load assumption: {p['gross_vehicle_mass_kg']:g} kg gross vehicle, "
             f"{p['vertical_load_factor']:g} g, shared by {p['rail_count']} rails. Each rail is screened "
             f"as a simply supported {p['support_span_mm']:g} mm beam with one central point load.", "",
             f"Comparison limits: {p['screening_yield_mpa']/p['yield_safety_factor']:g} MPa stress "
             f"(assumed {p['screening_yield_mpa']:g} MPa yield / {p['yield_safety_factor']:g}), "
             f"{p['support_span_mm']/p['deflection_span_ratio']:.1f} mm deflection. Verify actual steel properties.", "",
             "Bending uses shell-only inertia. It excludes any cover contribution, but assumes full bending "
             "continuity at segment joints. Local buckling, fatigue, joints, holes, bearing loads, "
             "torsional stiffness, whole-frame load sharing and impacts are not validated.", "",
             "Mass includes gross shell and cover steel plus an estimated splice allowance. "
             "It excludes crossmembers, mounts, axle structures and most hardware; it is not total chassis mass.", "",
             "The flat-width number is a conservative envelope bound, not an unfolded pattern. "
             "Part counts and bend counts are quote inputs; no supplier prices are assumed.", "",
             "## Lightest sections meeting these screens", "",
             "| Web / width / lip (mm) | Steel (mm) | Rail kit estimate (kg) | Stress (MPa) | Deflection (mm) |",
             "|---|---|---|---|---|"]
    for r in passing[:12]:
        lines.append(f"| {r['depth_mm']:g} / {r['width_mm']:g} / {r['lip_mm']:g} | {r['thickness_mm']:.2f} "
                     f"| {r['estimated_rail_kit_kg']:.1f} | {r['stress_mpa']:.1f} | {r['deflection_mm']:.2f} |")
    if passing:
        top = passing[0]
        (out / "concept.svg").write_text(concept_svg(top))
        lines += ["", f"The lightest screened option needs {top['segments_per_rail']} shell segments per rail, "
                  f"each approximately {top['part_length_mm']:.0f} mm long: {top['formed_parts']} formed shells, "
                  f"{top['cover_parts']} flat covers, {top['bends']} bends, plus joiners and fasteners.", "",
                  "![Rail and frame concept](concept.svg)"]
    (out / "report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "design/chassis-study.toml")
    parser.add_argument("--out", type=Path, default=ROOT / "out/chassis-study")
    args = parser.parse_args()
    with args.config.open("rb") as f:
        config = tomllib.load(f)
    rows = sweep(config)
    if not rows:
        raise ValueError("empty section search")
    write(config, rows, args.out)
    print(f"{len(rows)} sections; {sum(r['screen_pass'] for r in rows)} pass limited screens")
    print(args.out / "report.md")


if __name__ == "__main__":
    main()
