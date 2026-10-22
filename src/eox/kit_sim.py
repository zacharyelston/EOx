"""Connect concept inventories to an explicitly approximate vehicle model.

Steel masses are conserved without counting legacy fabricated-frame allowances
again. Body-layer CGs are coarse points; B0's complete electrical enclosure and
the rear-drive mass/envelope allowance remain conservative reference components.
"""
from functools import lru_cache
import tomllib

from eox.home_concepts import inventory, pack
from eox.params import ROOT, gauge, load_materials


@lru_cache(maxsize=128)
def layers(concept, material_id, length):
    with (ROOT/"design/home-concepts.toml").open("rb") as f:
        config = tomllib.load(f)
    c = dict(next(c for c in config["concepts"] if c["id"] == concept))
    if c["hybrid"]:
        raise ValueError("hybrid mass/control integration needs a separate study")
    c["frame_length_mm"] = length
    material = next(m for m in config["materials"] if m["id"] == material_id)
    g = gauge(load_materials(), material["material"], material["thickness_in"]*25.4)
    s = config["sheet"]
    width, height = [n*25.4 for n in s["size_in"]]
    masses, failures, moving = {}, 0, 0.0
    for name, parts in inventory(c, g).items():
        masses[name] = sum(p.mass_kg()*p.qty for p in parts)
        failures += pack(parts, width, height, s["edge_mm"], s["gap_mm"], s["trials"]) is None
        if name == "chassis":
            moving = sum(p.mass_kg()*p.qty for p in parts if p.part_no in ("A", "K"))
    return masses, failures, moving


def prepare(p):
    k, lo, f = p.kit, p.layout, p.steer_axle
    length = lo.wheelbase + lo.rear_overhang + lo.front_overhang
    masses, failures, moving = layers(k.concept, k.material_id, length)
    k.layer_mass_kg = sum(masses.values())
    k.front_mass_kg, k.rear_mass_kg = masses["front"], masses["rear"]
    k.nest_fails = failures
    lo.powerbox_x = lo.wheelbase + k.powerbox_front_offset
    lo.nose_x = lo.wheelbase - k.nose_setback
    lo.rail_depth_mm = k.rail_depth_mm
    # Keep moving front steel on the roll body; spread the remaining chassis
    # steel over the rail envelopes. No structural stiffness claim is implied.
    lo.rail_mass_kg_per_m = (masses["chassis"] - moving)/(2*length/1000)
    f.mass_kg = k.front_purchased_mass_kg + moving
    f.name = "Fabricated centre-pivot axle with purchased steering/hub allowance"
    lo.box_stand_mass_kg = lo.seat_pedestal_mass_kg = lo.hitch_mass_kg = 0
