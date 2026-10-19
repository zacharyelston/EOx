# EOX: open-source electric garden tractor from flat sheet

EOX is a small battery-electric garden tractor designed to be built from
laser-cut and press-brake-bent sheet metal ordered from SendCutSend (or any
shop with the same rules). Its look is low-poly and faceted (think cyber-truck),
because every panel is a flat sheet with straight bends.

The machine is built module by module. **Module 1 is the power box:** battery,
traction motor, controller and protection in a folded aluminium enclosure.

![Power box rev A1](docs/img/powerbox-exploded.png)

## How the design works

Everything is driven by one parameter file. Change a number, re-run, and the
geometry, flat patterns, safety checks and BOM all update together.

```
design/powerbox.toml   ─┐
design/materials.toml  ─┤  (SendCutSend K-factors, bend radii, limits)
                        ▼
              src/eox/powerbox.py   layout + sheet metal parts
                        │
     ┌──────────────────┼───────────────────┐
     ▼                  ▼                   ▼
 eox calc           eox build            eox bom
 checks report      STEP + DXF flats     purchased + fabricated
 (FAIL → exit 1)    assembly + STLs      cost and mass rollup
```

## Quick start

Needs [uv](https://docs.astral.sh/uv/). Blender is optional and only used for
the preview render.

```bash
uv run eox calc
```

```bash
uv run eox build
```

```bash
uv run eox bom
```

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P tools/render_preview.py -- out/cad/stl docs/img
```

- `calc` writes `out/powerbox-report.md` and exits 1 if anything FAILs.
- `build` writes `out/cad/`: STEP per part to order from SendCutSend, flat DXFs,
  and the assembly.
- `bom` writes `out/powerbox-bom.csv`.
- The Blender command renders `docs/img/*.png`.

Run the tests with `uv run pytest`.

## Repository

| Path | What |
|---|---|
| `design/` | Parameters (the source of truth) and material / SCS bend data |
| `src/eox/sheetmetal.py` | Bent-panel primitive: 3D solid, flat pattern, SCS rule checks |
| `src/eox/powerbox.py` | Component layout and the power box parts |
| `src/eox/calcs.py` | Engineering checks: drive, energy, electrical, thermal, structural, mass/CG |
| `bom/` | Hand-maintained purchased-parts list |
| `docs/` | [Tooling decision](docs/tooling.md), [safety requirements](docs/safety-requirements.md), [power box design](docs/powerbox.md) |
| `tools/` | Blender preview script |

## Status: power box rev A1

0 FAIL, 5 WARN, 110 PASS.

- **Thermal fixed.** A bulkhead now splits a sealed battery bay from a
  fan-ventilated motor bay. In full sun at 35 °C the pack runs at ≈ 44 °C
  (66 °C in rev A0), and ≈ 46 °C if the fan fails.
- **WARN: flat size.** Both shells' flats are at 97–98 % of SendCutSend's
  30 × 44 in bend limit.
- **WARN: charging in sun.** The pack reaches 42.9 °C against its 45 °C charge
  rating.
- **REF placeholders.** The battery, motor, controller and fan are generic
  envelopes until real parts are chosen.

Details are in [docs/powerbox.md](docs/powerbox.md#known-issues-rev-a1).

## Roadmap

1. **Power box:** real parts, then a prototype with thermocouples to validate the thermal model.
2. **Drivetrain:** about 40:1 total reduction (calc), chain or transaxle, brakes.
3. **Chassis and frame:** stability calc using the power box CG.
4. **Steering, seat, controls:** operator presence, no-mow-in-reverse, E-stop.
5. **Mower deck:** blade motors, 5 s blade stop.
6. **Low-poly body panels.**

## Safety

This is open hardware for builders, not a certified product. Read
[docs/safety-requirements.md](docs/safety-requirements.md) before building.
The battery pack must be a listed UL 2271 / IEC 62619 pack; do not build packs
from loose cells.

## License

TBD. Suggested: CERN-OHL-S-2.0 for the hardware design, MIT for the code.
