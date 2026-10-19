"""Load the TOML design files into attribute-access namespaces."""

from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace

from eox.sheetmetal import IN, Gauge

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "design"
OUT = ROOT / "out"


def _ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_ns(v) for v in obj]
    return obj


def load_materials() -> dict:
    with open(DESIGN / "materials.toml", "rb") as f:
        return tomllib.load(f)


def gauge(materials: dict, material: str, t_mm: float) -> Gauge:
    """Pick the SCS gauge whose thickness matches t_mm (to 0.05 mm)."""
    m = materials[material]
    for g in m["gauges"]:
        if abs(g["t_in"] * IN - t_mm) < 0.05:
            return Gauge(
                material=m["name"],
                t=g["t_in"] * IN,
                r=g["r_in"] * IN,
                k=g["k"],
                die=g["die_in"] * IN,
                min_flange=g["min_flange_in"] * IN,
                relief=g["relief_in"] * IN,
                max_bend_len=g["max_bend_len_in"] * IN,
                density=m["density"],
                yield_mpa=m["yield_mpa"],
                E_mpa=m["E_mpa"],
                k_w_mk=m["k_w_mk"],
            )
    have = ", ".join(f'{g["t_in"]}"' for g in m["gauges"])
    raise ValueError(f"{material}: no SCS gauge at {t_mm} mm (have {have})")


def load(name: str = "powerbox") -> SimpleNamespace:
    with open(DESIGN / f"{name}.toml", "rb") as f:
        p = _ns(tomllib.load(f))
    mats = load_materials()
    p.scs = _ns(mats["scs"])
    p.finish = _ns(mats["finish"][p.enclosure.finish])
    p.gauge = gauge(mats, p.enclosure.material, p.enclosure.thickness)
    p.doubler_gauge = gauge(mats, p.enclosure.material, p.enclosure.doubler_thickness)
    return p
