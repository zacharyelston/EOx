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


SHARED = ("units", "axle", "steer_axle", "powerbox", "course")
MODELS = tuple(sorted(f.stem for f in (DESIGN / "models").glob("*.toml")))


def load(model: str = "pro") -> SimpleNamespace:
    """Shared design files + one model file, merged into one namespace.

    Section names must be unique across files. A model may change shared
    values with an [overrides] table of dotted keys ("bus.units_installed" = 3),
    and pick its operating modes with [model] modes = [...]."""
    merged: dict = {}
    for path in [DESIGN / f"{n}.toml" for n in SHARED] + [DESIGN / "models" / f"{model}.toml"]:
        if not path.exists():
            raise FileNotFoundError(f"{path.relative_to(ROOT)} (models: {', '.join(MODELS)})")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        clash = merged.keys() & data.keys()
        if clash:
            raise ValueError(f"{path.name}: sections {sorted(clash)} already defined in another design file")
        merged.update(data)
    for dotted, value in merged.pop("overrides", {}).items():
        *path, key = dotted.split(".")
        node = merged
        for part in path:
            node = node[part]
        if key not in node:
            raise KeyError(f"override {dotted}: no such shared value")
        node[key] = value
    wanted = merged.get("model", {}).get("modes")
    if wanted:
        merged["modes"] = {k: v for k, v in merged["modes"].items() if k in wanted}
    p = _ns(merged)
    mats = load_materials()
    p.scs = _ns(mats["scs"])
    p.finish = _ns(mats["finish"][p.enclosure.finish])
    p.gauge = gauge(mats, p.enclosure.material, p.enclosure.thickness)
    return p
