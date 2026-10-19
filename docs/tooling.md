# Tooling decision: code-CAD as source of truth, Blender as the viewer

**Decision:** geometry, calculations and BOM all live in Python and read one
parameter file (`design/powerbox.toml`). Parts are modelled in
[build123d](https://github.com/gumyr/build123d) (open-source, OpenCascade
kernel). Blender is used for renders and styling studies, not for the parts we
order.

## Why not Blender for the parts

SendCutSend (SCS) takes either a flat DXF with bend lines or a STEP of the
formed part. For STEP orders, SCS requires:

- **One solid sheet-metal body** of uniform thickness.
- **Their own K-factor and inside radius.** Otherwise the part is rejected with
  "open contours".
- **Square bend reliefs.**

Source: <https://sendcutsend.com/guidelines/sheet-cutting/>.

Blender works with meshes. It has no B-rep solids, no STEP export, and no notion
of bend allowance, so a Blender model would have to be redrawn in CAD before it
could be ordered. Blender stays useful for:

- **Previews.** `tools/render_preview.py` renders `docs/img/*.png` from the
  generated STLs.
- **The low-poly body later on.** A cyber-truck shell is a polyhedral mesh, so
  Blender is a good place to sketch facets before they become bent panels.

## Why code-CAD (build123d) over GUI CAD

| Need | How the code approach covers it |
|---|---|
| Open-source collaboration | Text diffs and review on every change. No binary CAD files to merge. |
| Calcs stay in sync with geometry | Calcs read the same layout objects the CAD is built from, so they can't drift. |
| SCS rules enforced | `FlangedPanel.scs_checks()` runs on every part, every time. These checks cover flat size, minimum flange, the U-channel rule, hole-to-bend distance and hole-to-edge distance. |
| Swap a component | Edit the TOML (for example a new battery's dimensions), re-run, and the box, holes, flats, BOM and checks all update. |
| CI | `uv run pytest` and `uv run eox calc --model <m>` (exits non-zero on FAIL) can gate pull requests. |

## Alternatives considered

- **FreeCAD + SheetMetal workbench.** The best GUI option, and fine for
  contributors who prefer clicking. Import `out/cad/*.step` to inspect or modify
  parts. Changes made there don't flow back into the parameters.
- **Onshape / Fusion.** Good sheet-metal tools, but they're proprietary and
  cloud-hosted, which is a poor fit for an open-hardware source of truth.
- **OpenSCAD.** Has no STEP output and no bend model.

## How parts are modelled

`src/eox/sheetmetal.py` defines a `FlangedPanel`: a rectangular base with an
optional 90° flange on each edge. That covers every power box part (two shells,
a U-channel and an angle). Each panel produces:

- the formed 3D solid, exported to STEP for the SCS order;
- the flat pattern, using SCS's bend deduction, exported to DXF with `CUT` and
  `BEND` layers;
- its SCS manufacturability checks.

At box corners the long flanges run to the corner, the short flanges stop 0.5 mm
short, and a square relief clears the bend. If the tractor body needs non-90°
or multi-bend panels, `FlangedPanel` will need to grow, or the body will need a
second primitive.
