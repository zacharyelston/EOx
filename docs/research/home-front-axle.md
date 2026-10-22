# Home front axle: mechanism references

**Scope corrected 2026-10-22:** the donor-assembly recommendation below is
superseded. Golf-cart sourcing is for power components and controllers.
Home's chassis and axle structures are to be custom cut/bent steel parts
that the owner assembles. Use these OEM references to understand pivots,
steering geometry and load paths. See [the steel chassis study](../steel-chassis.md).

Research date: 2026-10-22. This records the proposed starting architecture;
it does not select a purchased part or change the H0 model.

## Superseded donor-assembly proposal

Use a conventional, non-driven lawn/garden-tractor front axle as Home's
starting reference. Retain golf-cart parts for rear traction. For the first
prototype, evaluate a complete donor front assembly and design the EOX frame
cradle around its measured mounting interfaces.

The useful distinction is between the fixed frame carrier and the moving
crossbeam:

- A cradle or pair of brackets bolts rigidly to the chassis.
- A centre pin, running fore-aft, lets the crossbeam rock in roll.
- The bosses/tubes at the beam ends carry the steering spindle kingpins.
- The spindles turn for steering and carry the wheel stub shafts.
- Positive roll stops limit movement before tyres, steering links or the beam
  contact the frame or deck.

The centre pivot allows axle articulation without requiring leaf-spring
suspension. A beam bolted rigidly to the frame at both ends does not provide
that motion. Steering rotation and axle roll are separate degrees of freedom.

John Deere's operator documentation explicitly identifies separate wheel
spindle/bushing lubrication and a front-axle centre-pivot fitting [3].

## Manufacturer references

| Reference | Confirmed from manufacturer documentation | Use for EOX |
|---|---|---|
| Husqvarna CTH19530, product 96051005500, 2012-04 | Axle 532418168; separate LH/RH spindle parts 532416845 and 532416846; two steering links, plus axle bushing and fasteners listed in the steering assembly [1] | Starting reference for the welded-beam family shown in the user's image. Inspect a complete matching assembly, including mounting and steering parts. |
| Husqvarna YTH22V46, product 96045006101, 2020-11 | Cast-iron axle 532195968; LH/RH spindles 532403087 and 532403088; sector steering, two draglinks, front-axle bushings and fasteners [2] | Alternative donor architecture. The listed steering system differs from H0's golf-cart rack. |
| John Deere lawn-tractor operator manual, front-axle lubrication | Separate spindle/hub fittings and a centre-pivot fitting [3] | Confirms the distinction between steering pivots and the rocking axle pivot. |

The part numbers above identify documented assemblies, not a claim that parts
interchange across models or that a particular seller has stock. Confirm
current replacements and exact donor model/year before ordering.

Manufacturer exploded views identify parts and relationships; they are not
dimensioned fabrication drawings or load-rating certificates. No axle width,
pin diameter, mass, load capacity or roll angle is adopted from photographs.

The CTH19530 parts list specifies 13 x 5.0-6 front tyres [1], while the
YTH22V46 lists 15 x 6.0-6 [2]. H0 currently assumes 18 x 8.50-8 front tyres.
Neither reference establishes compatibility with H0's wheel, hub or steering
envelopes. A wheel change also changes ground clearance and steering loads.

## What to reuse and what to fabricate

For a first prototype, source the beam, matching left/right spindles,
bushings, thrust hardware, pivot hardware, steering arms and links as a
matched assembly. Evaluate the donor steering gear and wheel/hub package
together. An inexpensive bare beam is only part of the front-end cost; a
listing called an axle may instead show a single spindle/stub axle.

Fabricate the EOX cradle and frame attachments from laser-cut/bent plates,
with suitable load paths into both rails. Check pin support, bracket bending,
local bearing and fastener loads. Replaceable bushings, accessible lubrication,
axial retention and service access belong in the design.

If a custom beam later becomes useful, use the same general architecture:
a folded/boxed crossmember, spindle carriers at its ends, and a supported
centre pivot. Preserve measured spindle geometry and use known replacement
wear parts. Welding carriers requires alignment control and may require
machining after welding; a bolted carrier needs a positively located,
calculated joint. Neither is a fabrication-ready design yet.

## Measurements and checks before choosing a donor

1. **Mounting:** pivot axis height, bore and pin sizes, bearing lengths,
   bracket spacing, axial retention, lubrication and roll stops.
2. **Wheel geometry:** track at the tyre centres, spindle shaft size and
   length, wheel offset, bearing spacing, caster and kingpin inclination.
3. **Steering:** arm locations, link lengths, available lock, toe change with
   axle roll, and steering effort. Verify the actual linkage rather than
   assuming the current rack or ideal Ackermann model transfers unchanged.
4. **Loads:** compare Home's calculated axle loads, obstacle and side loads
   with evidence for the donor assembly; include the new cradle and stops.
   OEM use on a smaller machine is not a load rating for EOX.
5. **Clearance:** full left/right lock at both roll stops, tyre-to-frame and
   tyre-to-deck clearance, drive-over deck clearance, and steering-link travel.
6. **Build data:** actual assembly mass/CG, condition, refurbishment parts,
   complete cost, and availability of replacement spindles and bushings.

## Simulation implications

The current `steer_axle.oscillates = true` branch in
`src/eox/sim/mjcf.py` removes roll stiffness but retains the leaf-spring
vertical `bounce` joint and its spring. It represents a sprung assembly with
free roll, not a conventional beam constrained to a centre roll pivot on a
rigid frame cradle.

The ML2 `home-layout` run uses that existing model. Preserve its results as
exploratory evidence; do not treat its winners as validation of the donor
architecture described here.

Before adopting a layout:

- Add an explicit fixed-carrier/centre-pivot configuration, with no vertical
  axle suspension joint. Keep tyre compliance and model roll-stop contact.
- Use the measured centre-pivot location in both the support-polygon
  calculations and the dynamic model. H0 currently places it at wheel-centre
  height as an assumption.
- Include cradle mass, actual steering hardware and the linkage's response
  to roll. The current steering actuators impose ideal knuckle angles.
- Compare H0, the existing sprung-pivot option, and the donor-style pivot
  model on the same bare/deck course before rerunning evolution.
- Check axle loads, joint motion, steering clearance, wheel lift and
  numerical convergence before adopting an apparent improvement.

## Sources

1. [Husqvarna CTH19530 illustrated parts list](https://www-static-nw.husqvarna.com/hbd/tdrdownload/v2/pub000098448/doc000248843/IPL/QLalTnicl1Q0SEVRFNMiIuPN9lM?httproute=True), PDF pages 17-20: steering and wheels.
2. [Husqvarna YTH22V46 illustrated parts list](https://www-static-nw.husqvarna.com/hbd/tdrdownload/v2/pub000080414/doc000140539/IPL/PXvJIrUAFHYNmKtxdze7qUgyxzc?httproute=True), printed pages 12-13: steering; printed page 18: wheels.
3. [John Deere operator manual: service lubrication](https://techinfo-omview.apps-prod-vpn.us.e06.c01.johndeerecloud.com/legacy/cceomview/omgx21821_h5/Output/OMGX21821_H510.html), spindle/bushing and centre-pivot instructions.
