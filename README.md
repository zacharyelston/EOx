# EOX: open-source electric garden tractor from flat sheet

EOX is a battery-electric garden tractor built from laser-cut and
press-brake-bent sheet metal, ordered from SendCutSend or any shop with the
same rules, plus off-the-shelf **golf-cart** drive parts.

The tractor's work is split into standard **3 HP units**: a golf-cart motor
plus its controller, on a shared **48 V bus**. Drive axles, the mower PTO and
hydraulic pumps all use the same unit; bigger jobs bundle several. Every panel
is a flat sheet with straight bends, which gives EOX its low-poly look.

![EOX Pro layout](docs/img/pro-layout.png)

## Two models, shared parts

| | EOX Pro | EOX Home |
|---|---|---|
| Layout | Articulated, centre pivot | Steering front axle |
| Drive | AWD: 2 golf-cart drive-axle modules | 2WD: 1 drive-axle module |
| Status | **In design** (`--model pro`) | Planned |

Both models share:

- the battery & distribution box;
- the drive-axle module;
- the 3 HP unit standard;
- attachments.

See [docs/architecture.md](docs/architecture.md).

## How the design works

Each model's numbers live in a few TOML files. Change a number, re-run, and the
geometry, flat patterns, engineering checks and BOM all update together.

```
design/units.toml      3 HP unit, 48 V bus, operating modes  ─┐
design/axle.toml       golf-cart drive-axle module            ├─ shared
design/powerbox.toml   battery & distribution box             │
design/materials.toml  SendCutSend K-factors, radii, limits   ─┘
design/models/pro.toml articulated layout, steering, module counts   ← per model
                │
                ▼
  src/eox/powerbox.py  box layout + sheet metal parts
  src/eox/tractor.py   whole-machine layout, masses, CG
                │
   ┌────────────┼──────────────────────┐
   ▼            ▼                      ▼
 eox calc     eox build               eox bom
 checks       STEP + DXF flats,       purchased (by module) +
 (FAIL→exit 1) layout + STLs          fabricated, cost + mass
```

## Quick start

You need [uv](https://docs.astral.sh/uv/). Blender is optional and only renders
the previews.

```bash
uv run eox calc --model pro
```

```bash
uv run eox build --model pro
```

```bash
uv run eox bom --model pro
```

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P tools/render_preview.py -- out/cad/pro/stl docs/img/pro-layout.png
```

- `calc` writes `out/pro-report.md` and exits 1 if anything FAILs.
- `build` writes `out/cad/powerbox/`:
  - a STEP per part, to order from SendCutSend;
  - flat DXFs;
  - an assembly STEP.

  It also writes `out/cad/pro/` with the whole-tractor layout.
- `bom` writes `out/pro-bom.csv`.
- The Blender command renders a preview image.

Run the tests with `uv run pytest`.

## Repository

| Path | What |
|---|---|
| `design/` | Parameters, the source of truth: shared files + `models/` |
| `src/eox/sheetmetal.py` | Bent-panel primitive: 3D solid, flat pattern, SCS rule checks |
| `src/eox/powerbox.py` | Battery & distribution box layout and parts |
| `src/eox/tractor.py` | Whole-machine layout for a model |
| `src/eox/calcs/` | Engineering checks, by domain: `bus`, `drive`, `vehicle`, `powerbox` |
| `bom/purchased.csv` | Purchased parts by module; each model sets its module counts |
| `docs/` | [Architecture](docs/architecture.md), [power box](docs/powerbox.md), [safety requirements](docs/safety-requirements.md), [tooling decision](docs/tooling.md), [component candidates](docs/component-candidates.md) |
| `tools/` | Blender preview script |

## Status: EOX Pro P0, power box B0

`eox calc --model pro` gives **0 FAIL, 7 WARN**.

- **Runtime:** one 100 Ah pack gives 1.4 h of mowing (target 1.5 h). Transport
  and backhoe runtimes are also short.
- **Gearing:** a stock golf-cart rear end needs 1.8× rated motor torque on a
  sustained 10° climb. A ~2:1 stage fixes it.
- **Bus current:** 185 A with 3 units running, against the pack's 200 A rating.
- **Thin margins:** BMS over-voltage trip (59.2 V of 60) and charging in the
  sun (43.9 °C of 45).
- **Not designed yet:** the axle subframes, the pivot and the deck are layout
  envelopes only.

Open work is tracked in the [GitHub issues](https://github.com/zacharyelston/EOx/issues).

## Safety

This is open hardware for builders, not a certified product. Read
[docs/safety-requirements.md](docs/safety-requirements.md) before building.

- The battery pack must be listed to UL 2271 or IEC 62619.
- Do not build packs from loose cells.

## License

MIT; see [LICENSE](LICENSE). A hardware-specific licence (for example
CERN-OHL-S-2.0) for the design files is an open question.
