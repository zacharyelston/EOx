# Design log

This log records what changed, why, and what we found. Newest entries are
first. Commit messages stay one line; the reasoning lives here and in the
pages each entry links to.

---

## 2026-10-19: Baselines against real machines (in progress)

**Why:** a test score means little until we know what a real product scores on
the same test. So real machines get modelled from their published specs and
run through the same checks and course as EOX.

**What changed:**

- **`src/eox/reference.py`:** builds a machine from a spec file in
  `design/reference/<name>.toml`.
  - It holds the published numbers: mass, wheelbase, tracks, tyres, rated
    slope and transaxle axle torque.
  - What makers don't publish (weight split, CG height) is estimated and
    marked REF.
  - Two mass lumps (engine and transaxle) are placed to match the published
    mass and the estimated weight split and CG height.
  - Two layouts: `lawn_tractor` (engine in front, open-diff rear transaxle,
    pivoting front axle, mid deck) and `articulated_rider` (front deck,
    centre pivot, optional AWD).
- **The simulation:** the MuJoCo model no longer needs an EOX power box. Drive
  limits can come from an axle-torque rating, and steering from a published
  moment.
- **`uv run eox baseline`:** runs EOX Home and Pro and every reference, and
  writes [baselines.md](baselines.md) and a status-grid figure.
- **Shared grip calc:** the grip-limit calc is now one function
  (`calcs.drive.grip_limit`), used by EOX and the references alike.

**Status:** specs are being gathered for the John Deere X350, Cub Cadet XT1
LT42, Ryobi 80V 42″ electric and Husqvarna R 316TX AWD. The machinery and its
tests are in; the reference files and results come next.

---

## 2026-10-19: Design trials and the front-battery question

**Why:** we need a way to evolve the designs, not just check them. A trial
asks one design question and answers it with evidence.

**What changed:**

- **`uv run eox evolve --trial <name>`:** a seeded genetic algorithm over a
  trial's genes (`src/eox/evolve/`).
  - Every candidate runs the full `eox calc` checks and the terrain course.
  - Ranking is feasible-first, then by a weighted score.
  - Evaluations are cached in `trials/<name>/history.jsonl`, so a re-run
    replays instantly, and `--generations` extends a run.
  - Today's design is always evaluated as the reference.
  - Results are written to `trials/<name>/`: `report.md`, `best.toml`
    (adoptable `[overrides]`) and a progress figure.
  - How to write a trial: [trials.md](trials.md).
- **Overrides and genes** can now reach list items (`layout.operator_cg.0`).

**Home layout, so the box and operator can move:**

- **Operator station:** the seat, floor, steering wheel and controls are now
  placed from the operator's position (`seat_height`, `floor_reach`,
  `steering_wheel_reach`). They used to be absolute positions tied to the box.
- **Seat bridge:** when the box isn't under the seat, the seat stands on a
  bridge (a post on each rail and a plate across), clear of the rear drive
  motor.
- **Box stand:** a box above the rails sits on a stand.
- **Frame mass:** follows rail length (`rail_mass_kg_per_m`, 5.0 kg/m), so a
  longer nose costs mass. H0 moves by −0.1 kg and its CG by 3 mm; no status
  changed.
- **Pivoting front axle option:** `steer_axle.oscillates = true` is now
  modelled in the simulation, with the roll stop at
  `steer_axle.oscillation_max_deg`.
  - On the course it cuts Home's wheel lift from 3.9 s to 1.2 s, and the
    side slope keeps every wheel loaded.
  - The calcs show the cost: the static working slope falls from 22.7° to
    19.8°, because the support becomes a triangle.

**New checks** (the first trial exploited each gap until it was closed):

- the steered front tyres must clear every part, lock to lock (a plan sweep
  about the kingpins);
- the steering column must clear the power box;
- the power box must sit within the frame, fore and aft.

**The first trial, `home-front-battery`:** can the Home carry its battery at
the front, like a tractor's engine?
([report](../trials/home-front-battery/report.md))

- **Answer:** yes, as a near tie with today's layout (score −26.6 vs −27.1).
- **The layout:** the box goes 640 mm up over the front axle, clear of the
  steered tyres and the column. The operator moves back over the rear axle,
  the deck moves back, and the PTO unit stands 50 mm further out.
- **Gains:** grip improves from 14.1° to 14.9°.
- **Costs:** the working slope falls from 22.7° to 20.6°, and the machine
  gains 10 kg.
- **The insight:** the gain comes from the operator's weight moving onto the
  driven wheels, not from the battery moving. A rear-drive machine wants its
  weight at the back.
- **Range limits:** three genes ended at theirs, so the layout is boxed in by
  real parts.

**Next trials to run:**

- a free box position, to test whether moving the operator back pays off
  without moving the box;
- a pivoting front axle as a gene, weighing the course against static
  stability.

---

## 2026-10-19: Terrain course in MuJoCo (PR 17)

**Why:** the static calcs can't say what happens when the ground twists, or
whether a kerb or ditch stops the machine. Details:
[simulation.md](simulation.md).

**What changed:** `uv run eox course` drives both models over a 7-obstacle
course, bare and with the deck fitted. The obstacles are a bump, kerb, ditch
and twist, 12° and 15° climbs, and a 17° side slope.

**Checks against the hand calcs:**

- Parked axle loads match the hand calc within 2 %.
- Home's grip limit lands about 1° below the calc. The open diff lets the
  lighter rear wheel set the limit.

**Getting the physics right took three changes:**

- **Tyre friction:** MuJoCo's contact rolling friction made the heightfield
  contacts chatter, so tyres use sliding plus torsional friction, and rolling
  resistance is a force at each wheel centre.
- **Rolling resistance:** as a force, it uses up the driven tyres' grip, as
  the calc assumes. As a torque it didn't.
- **Drive loop:** a stiff speed loop chattered against the tyre contact. A
  softer loop (`drive_gain = 50`) with integral action fixed it.

**Findings:**

- **Home's front axle:** it runs out of roll travel on twisting ground, and a
  front wheel lifts.
- **Home's 12° rating:** it has little margin.
- **Pro:** clears everything bare.
- **Pro's front deck:** it must pivot, because mounted rigidly it would dig in
  130–310 mm.

---

## 2026-10-18: The deck counts toward mass (PR 16)

**Why:** the initial design review
([review](reviews/initial-design-review.md)) found the 45 kg deck missing
from the vehicle mass.

**What changed:**

- **Mass:** the deck and its PTO unit are tagged masses at each model's
  mount (Home mid-mount, Pro front-mount).
- **Which configuration each check uses:**
  - drive climbs use the deck-fitted mass;
  - stability, steering and pivot loads take the worse of bare and
    deck-fitted.
- **Home:** with the deck, rear-tyre grip runs out near 14° on turf. So Home
  is rated for 12° climbs, with the aftermarket 15:1 gear set as standard
  (BOM G01). Pro keeps stock gearing and 15°.

---

## Earlier (PR 15 and before)

- **EOX Home:** the 2WD sibling of the articulated Pro, sharing the power box,
  the drive-axle module and the 3 HP unit standard.
- **Golf-cart geometry from factory manuals:** the motor sits sideways on an
  off-centre gear case, and the tracks and clearances are measured values
  ([research](research/golf-cart.md)).
- **Pro joint:** redesigned along industrial articulated-loader lines
  ([research](research/articulation.md)).
- **3 HP unit:** changed from an AC motor to a used or rebuilt golf-cart DC
  sepex motor, for simple and serviceable parts.
