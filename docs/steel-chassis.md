# Home: a steel kit assembled by its owner

The [product brief](product-brief.md) is the controlling design direction:
an appealing, useful open-source kit with one sheet per functional layer, judged on complete cost,
manufacture, assembly and ownership. The ladder-frame/rail family below is
one candidate, not the selected product architecture. Compare it with folded
side/floor structures that combine functions before developing its joints.

The newer [front-battery concept study](home-concepts.md) compares open-channel
chassis and separately nested front/rear body layers in mild steel and 304
stainless, including an optional generator carrier. Its inventories are
provisional; the section results below do not validate those different rails.

Direction confirmed 2026-10-22: golf-cart sourcing is for electrical power
components and controllers. The EOX chassis, axle structures, steering
supports and body are custom parts made from sheet and plate. A donor
golf-cart frame, front end or transaxle is not the starting architecture.

The owner orders finished cut/bent parts and standard hardware, then assembles
them with normal workshop hand tools. Bending, precision machining and any
required supplier subassembly happen before delivery. The first kit should
not require the owner to weld, line-bore, ream bearing seats or build a jig.

## Starting structure

One candidate is a modular ladder frame with deep folded steel side rails, bolt-on
crossmembers, and separate load-carrying modules for the rear drive, battery,
seat, front axle pivot and deck attachments. Keep electrical enclosures
separate from the chassis load path so they can be serviced or changed.

| Assembly | Fabricated from cut sheet/plate | Standard purchased parts |
|---|---|---|
| Side rails | Folded lipped channels, removable side covers, splice plates and local doublers | Structural bolts, washers, nuts and locating hardware |
| Crossmembers | Bent channels or plate assemblies with accessible bolted end connections | Fasteners and spacers |
| Front axle beam | Boxed plate or folded members on a supported centre roll pivot | Pin, replaceable bushings/bearings and thrust hardware |
| Steering ends | Plate-built knuckle/carrier assemblies with bolted precision bearing interfaces | Kingpins, wheel shafts/hubs, bearings, ball joints and links |
| Rear drive support | Plate bearing carriers, motor mount, reduction supports and guards | Shafts, bearings, sprockets/gears, chain/belt, differential or other selected drive mechanism |
| Seat, deck and controls | Replaceable brackets, mounting plates, footwell and guards | Seat, pedals, switches and wear components |

Known tractor designs remain references for load paths, articulation and
steering geometry. They do not force EOX to adopt a donor assembly's dimensions
or castings. Precision cylindrical parts should be bought or machined by a
supplier; laser-cut holes are not automatically precision bearing fits.

The rear driveline is a separate open decision. A generic differential and
shaft drive, or independently controlled wheel drives, changes the motor
count, braking, reduction, mass and current demand. Do not carry H0's donor
transaxle or runtime numbers into the new kit as if they were validated.

## Rail family to investigate

The first section study uses a vertical C web, horizontal top/bottom flanges,
and outward return lips. A flat cover bolts to the returns. Bolts and nuts
are accessible above and below the enclosed cavity, rather than requiring
a wrench deep inside a closed rail. The cover is removable for inspection.

The four-bend profile needs a new CAD primitive: the existing `FlangedPanel`
supports only one 90-degree bend per edge. A formed section with returns also
needs supplier review of its full bending sequence; bounding dimensions alone
cannot establish tooling access.

Start with a few discrete gauges and section depths. Increase section depth
and use local reinforcements where justified before making every part thick.
Keep enough clear space for the deck, wheels, steering and battery service.

Segment long rails into orderable parts, but count each splice as a structural
joint, extra material, fasteners and assembly work. Avoid placing a splice
at a highly loaded attachment or peak bending region without a checked load
path. Do not assume a segmented frame is equivalent to a continuous beam.

## Optimization in stages

1. **Section families.** Compare discrete gauges, depths, widths, return lips,
   cover arrangements and segment lengths. Reject obvious manufacturing and
   elastic-stiffness failures with inexpensive calculations. Enumerating this
   small space is more useful than a genetic search.
2. **Connections.** Parameterize splice lengths, bolt groups, locating
   features, doublers and end brackets. Check bearing, tear-out, net section,
   bolt loads, joint slip, fatigue and wrench access. Tabs locate parts;
   positive fasteners retain them. Tabs are not a substitute for calculating
   the joint's load path.
3. **Whole chassis.** Analyze frame torsion, unequal wheel reactions, braking,
   seat and battery loads, deck/hitch reactions, motor torque and ground
   strikes. Include local buckling and stress around holes and bends. Verify
   assembly preload and boundary conditions in structural analysis.
4. **Vehicle layout.** Feed actual fabricated masses and stiffness back into
   the vehicle model. Represent the front axle's centre pivot without an
   unintended vertical suspension joint, then evolve packaging and handling.
5. **Robustness and prototype.** Recheck leading candidates with manufacturing
   tolerances, different operators, ground conditions, timestep refinement
   and physical load/terrain tests. Release order files after those checks.

Use multiple objectives: complete quoted kit cost, delivered mass, unique
parts, bends, fastener count, assembly time, tool access, serviceability and
structural margins. Show tradeoffs rather than hiding everything in one score.
Nesting efficiency alone does not capture the cost of a bent and finished kit.

## First executable study

```bash
uv run python -m eox.chassis
```

Inputs are in `design/chassis-study.toml`; output is under
`out/chassis-study/`: a report, all candidates in CSV, and a section/frame
concept SVG. This is independent of the unchanged legacy H0/P0 vehicle models.

The initial sweep compares 144 lipped-channel sections. It uses a proposed
450 kg gross vehicle envelope at 3 g, equally shared between two rails, with
each rail screened as a 1,600 mm simply supported beam under a centre load.
The assumed comparison material has E = 200 GPa and yield = 250 MPa; the
stress screen uses a factor of two. Confirm properties for the actual grade
ordered; a generic mild-steel label does not establish them.

Bending stiffness uses the formed shell alone, excluding any cover composite
action. Full bending continuity at segment joints is still assumed. The
study does not prove joint strength, fatigue, buckling, torsional stiffness,
whole-frame behavior, clearance, fastener access or the cutting/bending
sequence. Results narrow the design space; they do not make a kit orderable.
The mass estimate covers the two rail shells/covers and a provisional splice
allowance, not the complete chassis. Exact flats and masses must come from
the next CAD model.

## Manufacturing and assembly rules

- Order bent parts from the shop. Use its actual material-specific thickness,
  bend radius, K-factor, minimum flanges and bend sequence.
- SendCutSend currently lists a 30 x 44 inch maximum flat for bending; bend
  length varies by thickness. Its U/C-channel base-to-flange rule is 2:1 [1].
  Use these as supplier constraints, not universal fabrication limits.
- Treat laser-cut dimensions, bend position/angle, coating and accumulated
  assembly tolerances separately. Locate critical pivots/bearing carriers
  from suitable datums rather than chaining several bend tolerances.
- Use one or two main fastener sizes where practical. Make structural nuts
  reachable, or specify rated captive hardware with a verified installation.
  Use removable panels to maintain access throughout the assembly sequence.
- Use tab/slot features for orientation and location with realistic clearance.
  Supplier guidance explicitly accounts for material thickness and coating;
  tight interference fits are not a general assembly strategy [2].
- Put adjustment slots in the tensioning/alignment system, with a checked
  means of retaining adjustment under load. Do not casually slot highly
  loaded bearing locations.
- Provide corrosion protection, drain paths, identification marks, a torque
  schedule, fastener BOM, exploded assembly drawings and replacement part
  files. Include finishing and packaging in quotes.

## Relationship to earlier work

The donor-assembly recommendation in `research/home-front-axle.md` is
superseded. Its mechanism references are still useful. The existing
`home-layout` run on ML2 was deliberately stopped during generation 15 after
14 completed generations. Its original snapshot, cache, logs and checkpoint
metrics are retained as legacy comparison data. It cannot
optimize fabricated chassis sections or joints and is not the new kit model.

The next useful artifact is a complete kit inventory and alternative folded
structures under an explicit sheet budget. Resolve stock size and scope,
then develop the chosen family into exact flats, joints and axle modules.
It should replace estimated structure masses before another large layout
evolution run. A rail-only result does not prove a one-sheet kit.

## Sources

1. [SendCutSend CNC bending specifications and guidelines](https://sendcutsend.com/services/cnc-bending/), checked 2026-10-22.
2. [SendCutSend tab-and-slot design guidance](https://sendcutsend.com/blog/mastering-tab-and-slot-design-for-efficient-metal-fabrication/), checked 2026-10-22.
