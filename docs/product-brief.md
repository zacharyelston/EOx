# EOX Home: open-source tractor built from sheet-sized modules

Product direction, 2026-10-22.

EOX should be a useful, appealing machine that a homeowner chooses to spend
money on, with a reproducible SendCutSend order and normal-tool assembly.
The fabricated parts are designed as functional layers, each fitting its own
source sheet. The tractor may use several sheets; attachments have their own
sheet budgets.
The public design must be easy to inspect, modify, manufacture and repair.

Passing a structural calculation, minimizing a rail's weight, or filling a
sheet efficiently is not sufficient to make a good product.

## Constraints that shape the product

- **One source sheet per functional layer.** Start with chassis; front
  fenders/covers/footrests; rear fenders/seat box/drive guards. A mower deck
  is a separate module, a wagon may use several sheets, and an optional
  hybrid carrier gets its own layer. Inventory every bracket, guard,
  structural doubler and splice in the appropriate layer.
- **First-choice sheet: 56 × 34 in (1422.4 × 863.6 mm).** This is the
  user's reference-sheet target per layer, not permission to make an
  oversized individual bent part. Supplier process limits apply separately.
- **Baseline and premium materials.** Start the comparison at 0.119 in
  mild steel, the existing supplier-listed near-1/8-in baseline, and
  0.125 in 304 stainless as the premium option. Regenerate flats using each
  material's bend data; do not reuse one material's DXF for the other.
  Keep a consistent material/gauge within each layer. Neither material is
  structurally approved by this selection.
- **Front battery, rear electric drive.** Package the battery in the former
  engine/nose area, low enough for useful handling while clearing steering
  sweep and axle roll. Retain the 100 Ah reference pack in the first
  comparison. A hybrid generator is optional, with explicit space, mass,
  charging-control and carrier requirements.
- **Standard purchased precision/wear parts.** Motors, controllers, battery,
  fasteners, bearings, bushes, pins, shafts, wheels, seat and cutting parts
  are listed separately. Golf-cart sourcing does not dictate donor axles,
  steering or chassis geometry.
- **Home assembly.** The supplier does cutting and bending. Avoid owner
  welding, precision machining, alignment jigs and specialized installation
  tools. Design assembly order and fastener access with the structure.
- **Simple, repeatable ordering.** Minimize unique parts, operations, bends,
  finishes and hardware varieties. Include their actual quoted costs.

## Optimize the whole structure

Compare at least these architecture families before committing to rails:

| Family | Potential benefit | Question to resolve |
|---|---|---|
| Folded side panels tied by a structural floor/battery cradle | One part can carry loads, protect wiring and form the finished body | Can the panels, joints and service openings resist torsion without consuming too much sheet? |
| Simple open channels tied by structural floor panels and crossmembers | Fewer covers and bends than individually boxed rails | How much does the floor/joint system contribute, including assembly slip? |
| Modular boxed rails with covers | Clear load paths and access to replaceable rail segments | Are the extra blanks, splices, bends and fasteners worthwhile for this product? |

Use folds, ribs and load-carrying panels to combine functions. A battery
cradle may also brace the frame; a side panel may also serve as a guard.
Preserve battery removal, inspection and replacement of damaged parts. Do
not make an enclosure structural without checking its joints and service
configuration.

Known tractor mechanisms remain useful references for steering and axle
roll. Their castings and donor dimensions do not define the fabricated kit.

## Product scorecard

| Dimension | Evidence needed |
|---|---|
| Useful mowing | Measured cut quality, area per charge and grass conditions; retain 1.5 h as the current runtime target until revised explicitly |
| Handling and comfort | Steering effort, maneuverability, wheel/deck clearance, operator reach, entry/exit and terrain behavior |
| Ownership value | Complete assembled-machine cost as well as the delivered fabricated-kit quote; transparent exclusions and refurbishment costs |
| Simplicity | Unique fabricated parts, bends, fasteners, tools, assembly steps and timed first-builder assembly |
| Appearance and finish | Coherent folded surfaces, protected wiring, accessible controls, usable footrests, clean edges, corrosion protection and drainage |
| Durability and repair | Structural and joint checks, load tests, replaceable wear parts, service access and independently orderable replacements |
| Manufacture by layer | Checked nest for every sheet/module, stock size/gauge, gaps, rotation restrictions, complete quantities and supplier acceptance |
| Open-source iteration | Parametric source, reproducible exports, meaningful diffs, versioned releases and reports showing consequences of each change |

Treat required load capacity, braking, clearances and manufacturing validity
as constraints. Compare viable candidates on quoted cost, assembly effort,
performance, appearance and material use. A lower single-number optimizer
score is not a substitute for those comparisons.

## Current concept comparison and the earlier rail study

The [front-battery concept comparison](home-concepts.md) uses the revised
layer rule. It generates compact, roomier and optional-hybrid layouts in
both materials. All 20 provisional layer inventories fit conservative
blank-envelope nests on 56 × 34 in reference sheets. That establishes a
packaging/material starting point; it does not establish complete joints,
vehicle performance or an orderable product.

`uv run python -m eox.chassis` compares 144 rail sections. It does not produce
a complete layer inventory or nested sheets and therefore cannot optimize
the modular product.

The previous closed-rail shells/covers alone used approximately 2.102 square
metres of gross strip area. A 56 × 34 in sheet has about 1.228 square metres.
That family therefore needs substantial revision or more than one chassis
sheet. It is not a selected architecture or a complete nesting result.

## The next design loop

1. Use the confirmed layer structure and first-choice sheet size. Keep the
   deck, wagon and optional hybrid module inventories explicit.
2. Develop the provisional Home concepts into complete interfaces and
   joints. Replace generic bracket allowances with actual parts and quantities.
3. Create a small number of manufacturable folded structures, integrating
   floor, sides and battery mounting where useful.
4. Generate exact flat patterns and nesting geometry from the same source as
   the formed model. Check overlaps, sheet edges, gaps, bend/rotation rules,
   and part quantities for each layer. Area alone does not prove a fit.
5. Check the structure and joints, packaging, steering, braking and deck
   behavior. Feed actual part masses into the vehicle simulation.
6. Get a complete cut/bend/finish quote and build a first assembly sequence.
   Eliminate complexity that does not improve the customer experience.
7. Use optimization to improve the viable families, then verify candidates
   through numerical refinement, prototype tests and another builder's
   experience before releasing a recommended order package.

## Release and ordering package

Each release should contain the parametric source, formed assembly, one
order file per fabricated part, quantities/material/finish manifest, checked
sheet layouts for every layer, hardware and purchased-parts BOM, exploded views, assembly
instructions, torque and adjustment information, test evidence and a complete
cost summary. A contributor must be able to regenerate these after a change.

Publish the sheet layout as proof of the material constraint and as a useful
reference for other shops. SendCutSend currently requests parts needing
bending or other additional processes as separate files; its production
nesting is not guaranteed to match the reference layout. Checked layer-sheet
designs and an accepted/quoted supplier order are separate checks [1].

Individual bent blanks must also meet SendCutSend's material-specific limits;
its currently listed maximum flat for bending is 30 x 44 in [2]. A larger
source sheet does not allow one oversized bent component.

## Sources

1. [SendCutSend sheet-cutting and nesting guidelines](https://sendcutsend.com/guidelines/sheet-cutting/), checked 2026-10-22.
2. [SendCutSend bending guidelines](https://sendcutsend.com/services/cnc-bending/), checked 2026-10-22.
