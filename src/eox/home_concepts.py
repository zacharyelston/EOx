"""Front-battery Home concepts and conservative blank-envelope packing.

One sheet per functional layer, in baseline mild steel or premium 304 stainless.
Uses the existing bend-allowance model. No holes, joints or vehicle physics
are validated. A successful nest covers only the explicit provisional inventory.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import random
import tomllib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from eox.params import ROOT, gauge, load_materials
from eox.sheetmetal import FlangedPanel, IN


@dataclass(frozen=True)
class Placement:
    key: str
    x: float
    y: float
    w: float
    h: float
    rotated: bool


def inventory(c, g):
    """Explicit functional part allowances, before joint / hole detailing."""
    layers = {"chassis": [], "front": [], "rear": []}
    layer = "chassis"

    def add(key, name, a, b, qty=1, flanges=None):
        layers[layer].append(FlangedPanel(key, name, a, b, g, flanges or {}, qty=qty))

    add("R", "Side channel half", c["frame_length_mm"] / 2,
        c["rail_depth_mm"], 4,
        {"+v": c["rail_flange_mm"], "-v": c["rail_flange_mm"]})
    add("S", "Rail splice plate", 180, 85, 4)
    add("B", "Battery support channel", 340, 70, 2, {"+v": 25, "-v": 25})
    add("H", "Battery hold-down strap", 340, 30, 2)
    add("E", "Battery end stop", 290, 30, 2, {"+v": 25})
    add("X", "Frame crossmember", 360, 65, flanges={"+v": 25, "-v": 25})
    add("M", "Rear motor mounting plate", 260, 200, flanges={"+v": 25, "-v": 25})
    add("A", "Front axle channel", 650, 100, flanges={"+v": 30, "-v": 30})
    add("V", "Axle pivot cheek", 110, 90, 2)
    add("K", "Kingpin bearing support", 90, 70, 4)
    add("T", "Steering support", 180, 110, flanges={"+v": 30})
    add("J", "Rear drive bearing support", 120, 100, 2)
    add("G", "Mount / deck hanger / gusset allowance", 70, 60, 12)
    add("Q", "Hitch plate", 180, 100, flanges={"+v": 25})
    layer = "front"
    add("F", "Footrest", c["foot_length_mm"], c["foot_width_mm"], 2, {"+v": 20})
    add("L", "Battery hood top", 580, 330, flanges={"+v": 25, "-v": 25})
    add("N", "Battery hood end", 330, 250, flanges={"+v": 20})
    add("O", "Battery hood side", 580, 240, 2, {"+v": 20})
    add("I", "Front fender", 420, 170, 2, {"+v": 25, "-v": 25})
    add("C", "Cowl / control bracket", 220, 160, flanges={"+v": 25})
    add("FG", "Front body mounting allowance", 60, 50, 8)
    layer = "rear"
    add("P", "Seat bridge", c["seat_length_mm"], c["seat_width_mm"],
        flanges={"+v": 25, "-v": 25})
    add("D", "Drive guard", 260, 120, 2, {"+v": 20})
    add("RF", "Rear fender", 600, 220, 2, {"+v": 30, "-v": 30})
    add("SB", "Seat box side", 350, 270, 2, {"+v": 25})
    add("RB", "Seat box rear", 360, 270, flanges={"+v": 25})
    add("SC", "Seat box service cover", 360, 300)
    add("RG", "Rear body mounting allowance", 60, 50, 8)
    if c["hybrid"]:
        layer = "hybrid"
        layers[layer] = []
        add("Y", "Generator carrier tray", 730, 560,
            flanges={"+v": 30, "-v": 30, "+u": 30, "-u": 30})
        add("Z", "Generator carrier brace", 450, 70, 2, {"+v": 25})
        add("W", "Operator heat shield allowance", 560, 300)
        add("U", "Generator mount doubler", 100, 80, 4)
    return layers


def pack(parts, width, height, edge=6, gap=4, trials=250):
    """Maximal-free-rectangle heuristic; None means no fit found, not impossibility.

    Inflate each box by the gap, with a matching virtual strip outside the
    usable right/top edges. This permits exactly `gap` between neighbours
    and exactly `edge` at the sheet boundary.
    """
    items = []
    for p in parts:
        w, h = p.flat_bbox()
        items.extend((f"{p.part_no}{i+1}", w, h) for i in range(p.qty))
    rng = random.Random(23)
    for trial in range(trials):
        order = items[:]
        if trial < 3:
            order.sort(key=lambda v: (v[1]*v[2], max(v[1:]), min(v[1:]))[trial], reverse=True)
        else:
            order.sort(key=lambda v: v[1]*v[2]*rng.uniform(.55, 1.45), reverse=True)
        free = [(edge, edge, width-2*edge+gap, height-2*edge+gap)]
        placed = []
        for key, w, h in order:
            choices = []
            for x, y, fw, fh in free:
                for rotated, a, b in ((False, w, h), (True, h, w)):
                    if a+gap <= fw+1e-8 and b+gap <= fh+1e-8:
                        dx, dy = fw-a-gap, fh-b-gap
                        choices.append(((min(dx, dy), max(dx, dy), y, x), x, y, a, b, rotated))
            if not choices:
                break
            _, x, y, a, b, rotated = min(choices)
            placed.append(Placement(key, x, y, a, b, rotated))
            right, top = x+a+gap, y+b+gap
            split = []
            for fx, fy, fw, fh in free:
                fr, ft = fx+fw, fy+fh
                if right <= fx or x >= fr or top <= fy or y >= ft:
                    split.append((fx, fy, fw, fh))
                else:
                    if fx < x: split.append((fx, fy, x-fx, fh))
                    if fr > right: split.append((right, fy, fr-right, fh))
                    if fy < y: split.append((fx, fy, fw, y-fy))
                    if ft > top: split.append((fx, top, fw, ft-top))
            free = []
            for r in sorted(set(split)):
                if not any(s != r and s[0] <= r[0] and s[1] <= r[1]
                           and s[0]+s[2] >= r[0]+r[2]-1e-8
                           and s[1]+s[3] >= r[1]+r[3]-1e-8 for s in split):
                    free.append(r)
        else:
            validate_nest(parts, placed, width, height, edge, gap)
            return placed
    return None


def validate_nest(parts, placed, width, height, edge, gap):
    def require(ok, message):
        if not ok:
            raise ValueError(message)

    expected = {f"{p.part_no}{i+1}": p.flat_bbox() for p in parts for i in range(p.qty)}
    require(Counter(p.key for p in placed) == Counter(expected.keys()), "missing / repeated parts")
    for i, a in enumerate(placed):
        w, h = expected[a.key]
        if a.rotated: w, h = h, w
        require(abs(a.w-w) < 1e-6 and abs(a.h-h) < 1e-6, "wrong envelope")
        require(a.x >= edge-1e-6 and a.y >= edge-1e-6, "edge margin")
        require(a.x+a.w <= width-edge+1e-6 and a.y+a.h <= height-edge+1e-6, "outside sheet")
        for b in placed[i+1:]:
            require(a.x+a.w+gap <= b.x+1e-6 or b.x+b.w+gap <= a.x+1e-6
                    or a.y+a.h+gap <= b.y+1e-6 or b.y+b.h+gap <= a.y+1e-6, "overlap / gap")


def study(config):
    s = config["sheet"]
    mats = load_materials()
    w, h = (n*IN for n in s["size_in"])
    scs = SimpleNamespace(**mats["scs"])
    results = []
    for material in config["materials"]:
        g = gauge(mats, material["material"], material["thickness_in"]*IN)
        for c in config["concepts"]:
            layers = []
            for name, parts in inventory(c, g).items():
                area = sum(p.flat_area_mm2()*p.qty for p in parts)
                bbox_area = sum(p.flat_bbox()[0]*p.flat_bbox()[1]*p.qty for p in parts)
                nest = pack(parts, w, h, s["edge_mm"], s["gap_mm"], s["trials"]) if bbox_area <= w*h else None
                failures = [f"{p.part_no}: {ch.name}" for p in parts for ch in p.scs_checks(scs) if ch.status == "FAIL"]
                layers.append(dict(name=name, parts=parts, area=area, bbox_area=bbox_area,
                                   sheet_area=w*h, mass=area*g.t*g.density*1e-9,
                                   count=sum(p.qty for p in parts),
                                   bends=sum(len(p.flanges)*p.qty for p in parts),
                                   nest=nest, failures=failures))
            results.append(dict(concept=c, material=material, layers=layers))
    return results


def write(config, results, out):
    out.mkdir(parents=True, exist_ok=True)
    sw, sh = config["sheet"]["size_in"]
    report = ["# Front-battery Home: one sheet per layer", "",
              "Concept geometry and provisional inventory only. Not a structural result, quote or order package.", "",
              f"Reference sheet for each layer: {sw} × {sh} in. One material/gauge throughout each candidate.",
              "Layers: chassis; front fenders/covers/footrests; rear fenders/seat box/drive guards; optional hybrid carrier.",
              "Mower deck and wagon are separate, unmodelled modules with their own sheet budgets.",
              "The front battery retains the reference 520 × 270 × 220 mm, 45 kg pack; no capacity reduction is assumed.", "",
              "| Material | Concept | Layer | Blanks | Bends | Flat area / sheet | Part mass | Nest |",
              "|---|---|---|---:|---:|---:|---:|---|"]
    manifest = []
    for result in results:
        c, m = result["concept"], result["material"]
        for r in result["layers"]:
            fit = "Envelope fit" if r["nest"] else ("Area exceeds sheet" if r["area"] > r["sheet_area"] else "No fit found")
            report.append(f'| {m["id"]} {m["thickness_in"]} in | {c["id"]} | {r["name"]} | {r["count"]} | {r["bends"]} | {100*r["area"]/r["sheet_area"]:.1f}% | {r["mass"]:.1f} kg | {fit} |')
            folder = out/m["id"]/c["id"]/r["name"]
            folder.mkdir(parents=True, exist_ok=True)
            with (folder/"inventory.csv").open("w") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "name", "qty", "formed_a_mm", "formed_b_mm", "flanges_mm", "blank_w_mm", "blank_h_mm", "flat_area_each_mm2", "mass_each_kg"])
                for p in r["parts"]:
                    writer.writerow([p.part_no, p.name, p.qty, p.A, p.B, json.dumps(p.flanges), *p.flat_bbox(), p.flat_area_mm2(), p.mass_kg()])
            if r["nest"]:
                (folder/"nest.json").write_text(json.dumps([p.__dict__ for p in r["nest"]], indent=2)+"\n")
            else:
                (folder/"nest.json").unlink(missing_ok=True)
            manifest.append(dict(material=m["id"], concept=c["id"], layer=r["name"],
                                 area_percent=100*r["area"]/r["sheet_area"], mass_kg=r["mass"],
                                 count=r["count"], bends=r["bends"],
                                 envelope_fit=bool(r["nest"]), basic_manufacturing_failures=r["failures"]))
    report += ["", "Masses cover gross unperforated steel parts, with bend deductions and reliefs from the existing sheet-metal model; hardware, coatings and purchased components are additional.",
               "All included quantities are counted. Generic mount/hanger/gusset blanks reserve material but are not detailed joints.",
               "The 4 mm inter-part gap, 6 mm edge reserve and unrestricted 90-degree rotations are study assumptions requiring supplier confirmation.",
               "Mount holes, fastener access, axle joints, transmission, steering linkage, braking, electrical casing and layer interfaces remain unresolved.",
               "Bodywork and seat-box masses must feed vehicle physics; the legacy H0 simulation does not describe these concepts.",
               "A successful bounding-box nest conservatively places this provisional inventory. It does not prove a complete machine, strength, tooling access or an accepted order.",
               "A negative heuristic packing result is not proof that no revised nest or design can fit.", ""]
    for row in manifest:
        if row["basic_manufacturing_failures"]:
            report += [f'## {row["material"]} / {row["concept"]} / {row["layer"]}: screen failures', ""]
            report += ["- "+f for f in row["basic_manufacturing_failures"]] + [""]
    (out/"report.md").write_text("\n".join(report))
    (out/"summary.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (out/"concepts.svg").write_text(drawing(config, results))


def drawing(config, results):
    """Assembled packaging sketches beside independently checked layer nests."""
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="1560" viewBox="0 0 1560 1560">',
           '<style>text{font-family:Arial,sans-serif;fill:#18332f}.title{font-size:30px;font-weight:bold}.h{font-size:22px;font-weight:bold}.b{font-size:16px}.s{font-size:14px}.tiny{font-size:9px}</style>',
           '<rect width="1560" height="1560" fill="#f4f4ee"/>']

    def text(x, y, val, cl="b", **attrs):
        svg.append(f'<text x="{x}" y="{y}" class="{cl}" '+" ".join(f'{k}="{v}"' for k,v in attrs.items())+f'>{html.escape(str(val))}</text>')

    def rect(x, y, w, h, fill, stroke="#18332f", **attrs):
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" '+" ".join(f'{k}="{v}"' for k,v in attrs.items())+'/>')

    text(35, 48, "EOX HOME / FRONT BATTERY / MODULAR SHEET KITS", "title")
    text(35, 78, "One 56 × 34 in sheet per functional layer • baseline 0.119 in mild steel / premium 0.125 in 304 stainless")
    text(35, 104, "Packaging and material study. Provisional blanks, no joint holes; no structural validation or released order files.", "s")
    colors = {"chassis": "#8fae9c", "front": "#b9d584", "rear": "#8cbcb7", "hybrid": "#e4b77f"}
    baseline = [r for r in results if r["material"]["id"] == "mild"]
    for i, result in enumerate(baseline):
        c = result["concept"]
        y = 130+i*440
        rect(25, y, 1510, 422, "#fff", "#d4ddd5", rx="12")
        text(45, y+32, f'{c["id"]} / {c["name"]}', "h")
        text(45, y+58, f'Wheelbase {c["wheelbase_mm"]} mm • frame {c["frame_length_mm"]} mm • front 45 kg battery', "s")
        scale = .205
        ox, gy = 280, y+300
        def xx(x): return ox+x*scale
        def zz(z): return gy-z*scale
        wb = c["wheelbase_mm"]
        for x, z, rad in [(0, 250, 250), (wb, 180, 180)]:
            svg.append(f'<circle cx="{xx(x)}" cy="{zz(z)}" r="{rad*scale}" fill="#293936" stroke="#102c26" stroke-width="3"/>')
            svg.append(f'<circle cx="{xx(x)}" cy="{zz(z)}" r="{rad*scale*.44}" fill="#d4dacf"/>')
        rect(xx(-150), zz(345), c["frame_length_mm"]*scale, c["rail_depth_mm"]*scale, colors["chassis"])
        rect(xx(250), zz(150), 600*scale, 80*scale, "#b0b9a4", "#667559")
        text(xx(290), zz(105), "DECK*", "tiny")
        bx = wb+config["packaging"]["battery_front_axle_offset_mm"]
        rect(xx(bx-290), zz(640), 580*scale, 280*scale, colors["front"])
        rect(xx(bx-260), zz(600), 520*scale, 220*scale, "none", "#637b35", **{"stroke-dasharray":"4 3"})
        text(xx(bx-240), zz(480), "FRONT BATTERY BAY", "tiny")
        rect(xx(wb-210), zz(410), 420*scale, 25*scale, colors["front"])
        rect(xx(-200), zz(540), 600*scale, 30*scale, colors["rear"])
        rect(xx(150), zz(540), 350*scale, 195*scale, colors["rear"])
        text(xx(180), zz(415), "SEAT BOX", "tiny")
        rect(xx(-105), zz(355), 220*scale, 140*scale, "#478c88")
        text(xx(-90), zz(275), "DRIVE", "tiny")
        rect(xx(150), zz(610), 310*scale, 55*scale, "#263b35")
        rect(xx(150), zz(825), 40*scale, 240*scale, "#263b35")
        svg.append(f'<path d="M {xx(700)} {zz(340)} L {xx(560)} {zz(780)}" stroke="#29433a" stroke-width="5"/>')
        svg.append(f'<ellipse cx="{xx(560)}" cy="{zz(780)}" rx="25" ry="6" fill="none" stroke="#29433a" stroke-width="4"/>')
        if c["hybrid"]:
            rect(xx(-900), zz(940), 700*scale, 570*scale, colors["hybrid"], "#a56326", **{"stroke-dasharray":"7 4"})
            text(xx(-875), zz(655), "GENERATOR", "tiny")
            text(xx(-875), zz(585), "40 kg dry ref.", "tiny")
            svg.append(f'<path d="M {xx(-900)} {zz(355)} H {xx(-100)}" stroke="#a56326" stroke-width="5"/>')
        text(45, y+327, "REAR ←   Side elevation (schematic)   → FRONT", "s")
        mildmass = sum(l["mass"] for l in result["layers"])
        ss = next(r for r in results if r["concept"]["id"] == c["id"] and r["material"]["id"] == "304")
        ssmass = sum(l["mass"] for l in ss["layers"])
        text(45, y+362, f'{len(result["layers"])} layer sheets • steel parts {mildmass:.1f} kg mild / {ssmass:.1f} kg 304', "b")
        count = sum(l["count"] for l in result["layers"])
        bends = sum(l["bends"] for l in result["layers"])
        text(45, y+388, f'{count} provisional blanks / {bends} bends; hardware and purchased parts additional', "s")
        for j, layer in enumerate(result["layers"]):
            sx, sy = 770+(j%2)*370, y+58+(j//2)*176
            sw = 250
            sh = sw*34/56
            text(sx, sy-13, f'{layer["name"].upper()} / {100*layer["area"]/layer["sheet_area"]:.0f}% area / {layer["mass"]:.1f} kg', "s")
            rect(sx, sy, sw, sh, "#eef1e7", "#6f8979")
            if layer["nest"]:
                factor = sw/(56*IN)
                for p in layer["nest"]:
                    rect(sx+p.x*factor, sy+p.y*factor, p.w*factor, p.h*factor, colors[layer["name"]], "#fff")
                    text(sx+p.x*factor+2, sy+p.y*factor+9, p.key, "tiny")
            else:
                text(sx+12, sy+60, "No envelope fit found", "s")
                text(sx+12, sy+88, "Revise this layer", "s")
        if len(result["layers"]) == 3:
            text(1140, y+275, "Each rectangle: 56 × 34 in", "s")
            text(1140, y+302, "6 mm edge / 4 mm gaps", "s")
            text(1140, y+329, "90° rotations allowed", "s")
            text(1140, y+356, "Mild-steel blank envelopes.", "s")
            text(1140, y+383, "304 checked independently.", "s")
    text(35, 1484, "* Deck and wagon have independent sheet budgets; neither is designed in this comparison. Same battery capacity in every concept.", "s")
    text(35, 1509, "Nests prove only this provisional inventory. Joint design, steering sweep, strength, body clearances and supplier acceptance remain open.", "s")
    text(35, 1534, "Hybrid: reserve service/cooling/exhaust space, fuel mass and BMS controls; no onboard running approval or runtime claim is implied.", "s")
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/"design/home-concepts.toml")
    parser.add_argument("--out", type=Path, default=ROOT/"out/home-concepts")
    args = parser.parse_args()
    with args.config.open("rb") as f:
        config = tomllib.load(f)
    results = study(config)
    write(config, results, args.out)
    print((args.out/"report.md").read_text())


if __name__ == "__main__":
    main()
