# Design log

This log records what changed, why, and what we found. Newest entries are
first. Commit messages stay one line; the reasoning lives here and in the
pages each entry links to.

---

## 2026-10-19: Baselines against real machines

**Why:** a test score means little until we know what a real product scores
on the same test.

**What changed:**

- **`design/reference/`:** four machines with their sources. The research
  covered spec pages, operator's manuals and Tuff Torq transaxle sheets.
  - **John Deere X350:** K46, rated 15°.
  - **Cub Cadet XT1 LT42:** TL-200, rated 15°.
  - **Ryobi 80V 42″ RYRM8060:** electric. Discontinued; Ryobi's last 42″
    lawn tractor. Rated 15°.
  - **Husqvarna R 316TX AWD:** articulated, front Combi 103 deck, rated 10°.
    Not sold in the US.
- **`src/eox/reference.py`:** builds each machine with its published mass,
  wheelbase, tracks, tyres and rating. Two mass lumps are placed to match the
  estimated weight split and CG height (REF).
- **`uv run eox baseline`:** writes [baselines.md](baselines.md) and a
  status-grid figure.
- **Ratings:** each machine is scored against its own climb and cross-slope
  ratings. The EOX models now state their cross-slope rating, 17°, the label
  value they already used.
- **Per-axle drive torque:** for AWD machines with two different transaxles.

**Modelling choices the first run forced:**

- **Drive torque:** transaxle makers publish a continuous axle-torque rating,
  and the hydrostatic relief allows more. With the rating as a hard ceiling,
  a Deere couldn't climb the 15° it is rated for. So each reference gets at
  least the torque to climb its rated slope with the operator, plus 20 %.
- **Frame ends:** real frames rise at the nose and tail. Rails modelled at
  ground clearance all the way out made every lawn tractor dig into the
  ditch.
- **Configuration:** all machines are compared deck-fitted, the way they
  mow. A reference calibrated with its deck turns tail-heavy if the deck
  comes off.

**Findings** (deck fitted):

- **Wheel lift:** the lawn tractors' pivoting front axles keep every wheel
  down on the twist and the side slope. Home's leaf-sprung axle lifts a
  wheel on both: more evidence for a pivoting axle (a trial gene now exists).
- **Stability:** Home's working slope is 24°, against 13–14° for the lawn
  tractors (half the static tip angle).
- **Grip:** the lawn tractors climb on grip to about 16°, against Home's 14°.
  Their higher CG loads the driven wheels more on a climb, and costs them
  stability.
- **Pro vs Husqvarna:** both grip to 22° with AWD. The Pro is rated higher
  (15° vs 10°) and is more stable (20° vs 14°).
- **Front decks:** both front-deck machines need a pivoting deck.
- **Deck float:** every mid-deck machine, real or EOX, needs about 105 mm of
  float on the twist. The 75 mm allowance (REF) is probably too strict; worth
  revisiting.
- **Weight and runtime:** EOX is 50–85 kg heavier, and runs 1.3–1.4 h on a
  charge against the Ryobi's 1.0–1.25 h.

**Caveats:**

- Weight split and CG height are estimated for every reference.
- The track widths of the three US tractors are estimated.
- Prices: dealer price for the Deere; launch MSRP for the discontinued Ryobi;
  EU price, converted and without its deck, for the Husqvarna.

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
