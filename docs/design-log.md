# Design log

This log records what changed, why, and what we found. Newest entries are
first. Commit messages stay one line; the reasoning lives here and in the
pages each entry links to.

---

## 2026-10-21: Overnight trials, levels of detail and fidelity

**Why:** five design questions the work had raised, run as a series, plus a
way to trade simulation detail for speed and check the trade.

### The trials

Reports are in `trials/<name>/report.md`.

| Trial | Answer |
|---|---|
| `home-pivot-axle` | **Pivot the front axle.** Wheel lift drops from 5.8 s to 0.1 s, the side slope keeps about 400 N on its lightest wheel (was 0), and course WARNs fall from 4 to 1. It costs working slope (22.7° → 19.8°). It wants a stop of 15° or more, which is the range limit. Springs barely matter once it pivots. |
| `home-15-degrees` | **A 15.5° rating is reachable.** Drive tyres at 8 psi, the deck moved back to 560 mm and the PTO unit out to 480 mm, on the 15:1 gears. Grip goes 14.2° → 15.9°, but the motor sits at 3.8× rated, close to its 4× peak. The rating, pressure and deck position all ended at their range limits. |
| `home-layout-free` | **Keep the battery where it is**, low under the seat. The only gain is moving the deck back and the PTO unit out (grip 14.2° → 14.7°). |
| `home-wet-ground` | **No setup clears the kerb on soft ground** (cone index 200 kPa). The best (8 psi tyres, deck back) lifts grip from 6.3° to 8.1° and cuts stuck obstacles from 3 to 1. Soft ground needs driven front wheels. |
| `pro-steering` | **Keep the 45 mm cylinder and 4 L/min pump; raise relief to 110 bar and the lever arm to 140 mm.** Margin goes from 12 % to 44 %, lock to lock is 3.9 s (target 4 s), and the pump draws 11 W more. The first run had no ceiling on margin and trivially chose the biggest cylinder at the highest pressure; it was re-posed with caps. |

**What recurs:** every Home trial moves the deck back and the PTO unit out,
and lowers the drive-tyre pressure.

**Candidate next trial:** combine them, with a pivoting axle, about 8–10 psi
tyres, the deck back and a 15° rating. Also widen the ranges that ended at
their limits.

### Engine changes

- **Quieter log:** one line per generation, plus the design only when a new
  best appears. The repetition in the overnight log came from reprinting an
  unchanged best every generation.
- **Early stopping:** `patience`, default 8 generations without a better
  design.
- **`cap` on objectives:** credit stops at a target.
- **`[trial.overrides]`:** values fixed for every design in a trial.
- **Several `--trial` flags:** run a series.
- **New metrics:** steering margin, lock-to-lock time, bore, pump draw, rim
  force.
- **Exploration was fine all along.** The trials evaluated 323–541 distinct
  designs each, with every gene explored widely. They converged at different
  speeds; `home-15-degrees` kept improving for 20 generations.

### Levels of detail

Profiling one course run gave 82 % MuJoCo physics (C), 18 % our Python, and
the genetic algorithm next to nothing. A Rust port would recover at most the
18 %, so it isn't worth the effort for now; bigger hardware is the easier
lever. Instead, `course.lod` picks how much physics to ask for:

| Level | Settings | Speed vs high |
|---|---|---|
| high | today's validated settings | 1× |
| medium | 4 ms step; only parts within 350 mm of the ground collide | 1.3–1.7× faster |
| low | 6 ms step, 25 Hz driver, 10 cm terrain grid | 2–3.3× faster |

**Checked against high**, both models, bare and deck-fitted, 28 obstacle
results per level:

- **Medium:** every status matches except one borderline deck-float case (76
  against 73 mm, either side of the 75 mm allowance).
- **Low:** every status matches. Low is harsher on climbs near the grip limit.
- **Rejected:** fewer solver iterations and a pyramidal friction cone, since
  both changed results.

### Fidelity: do low-detail sweeps change the designs?

**No, for the two trials checked** (`uv run eox fidelity`):

| Trial | Run time, low vs high | Improvement captured | Same decisions? |
|---|---|---|---|
| `home-pivot-axle` | 9 vs 22 min | 99.6 % | Yes: pivot, 15° stop. The springs differ, but they don't matter once the axle pivots. |
| `home-15-degrees` | 11 vs 24 min | 100 % | Yes: 15.5°, 8 psi, deck at 560, operator and battery unchanged. Low picked the chain stage over the 15:1 gears, buying torque margin because its climbs are harsher; scored at high the two tie. |

In both, the top designs score within 1–3 % of the improvement of each other.
Their order is noise at either level, so rank agreement says little; the
improvement captured is the measure to read.

**How to use it:** sweep at low detail, then confirm the winner at high,
which the fidelity check does.

---

## 2026-10-21: Licence: CERN-OHL-W, MIT and CC-BY-SA

**Why:** EOX is hardware, and MIT is a software licence. This settles
[issue 13](https://github.com/zacharyelston/EOx/issues/13).

**Options considered:**

- **Strongly reciprocal (CERN-OHL-S):** every derivative shares everything.
- **Permissive (CERN-OHL-P or MIT):** derivatives may be closed.
- **No licence:** rejected. Our own licence never bound us; we hold the
  copyright. Removing it would have made EOX "all rights reserved" for
  everyone else, and wouldn't have loosened any third-party asset's terms.

**What changed:** EOX is now licensed in three parts.

- **Hardware design files** (`design/`, `bom/`, and the CAD and cut files
  made from them): CERN-OHL-W-2.0. Anyone may build, sell and modify EOX.
  Changes to EOX's own design files must be shared, but makers can add their
  own closed attachments and body panels.
- **Software:** MIT, as before.
- **Docs and images:** CC-BY-SA-4.0.

**Files:**

- **`LICENSES/`:** the official texts (CERN's own CERN-OHL-W, SPDX's
  CC-BY-SA-4.0, our MIT).
- **`LICENSE`:** a map of what is under which licence.
- **`REUSE.toml`:** licences by path. The repo passes `reuse lint` (REUSE
  3.3).
- **`NOTICE`:** the CERN-OHL notice with the source location, asking anyone
  who builds a machine to show it on the machine or in its manual.
- **`assets/README.md`:** the licences we accept for third-party assets
  (CC0, CC-BY, CC-BY-SA, permissive) and the ones we don't (non-commercial,
  editorial-only, GrabCAD's default, branded models).
- **`CREDITS.md`:** credits for dependencies and assets.
- **`pyproject.toml`:** declares the Python package MIT.

**Earlier versions:** copies taken under MIT, up to `632ed92`, stay MIT.

---

## 2026-10-19: Tyre pressure and ground strength

**Why:** to test grip by changing tyre air pressure. Until now every tyre had
a fixed traction of 0.5 and a rolling resistance of 0.10, whatever its size,
pressure or load.

**What changed:**

- **`src/eox/tyres.py`:** works out tyre deflection and stiffness from size
  and pressure with a membrane model, and grip and rolling resistance from
  the Brixius equations (ASAE D497), against the ground's cone index.
- **`design/ground.toml`:** lawn turf, cone index 400 kPa, chosen so an EOX
  drive tyre at 12 psi reproduces the old turf values.
- **Pressures:**
  - **EOX:** 12 psi drive tyres and 14 psi steering tyres (REF).
  - **Real machines:** their makers' figures. Deere 14/10 psi, Ryobi 15/12,
    Husqvarna 8.5 (0.6 bar).
- **Calcs:**
  - The machine's traction and rolling resistance now come from its tyres at
    their loads.
  - The grip limit evaluates each axle's tyres at the climb's own load split.
  - New checks: tyre deflection under 25 % of section height, and pressure
    within the tyre's rating.
- **Sim:**
  - Each wheel rides on a spring with its tyre's stiffness, above a stiff
    contact.
  - Grip and rolling resistance follow each wheel's live load.
  - MuJoCo's soft contact squashes only about 1 mm, and a heightfield
    contact shares a wheel's load across several points, so contact softness
    couldn't represent a 13 mm tyre squash. The settled squash in the sim now
    matches the formula.
- **Tools:**
  - `uv run eox tyres --model <m>` sweeps the drive-tyre pressure on three
    grounds.
  - Pressures and the ground can be trial genes.

**Findings** (deck fitted, steepest climb on grip):

| Ground | Home, 8 / 12 / 20 psi | Pro, 8 / 12 / 20 psi |
|---|---|---|
| Firm dry lawn (cone index 1000) | 19.3 / 19.1 / 18.8° | 26.8 / 26.7 / 26.5° |
| Lawn turf (400) | 15.3 / 14.2 / 13.0° | 23.6 / 22.7 / 21.6° |
| Soft wet lawn (200) | 7.8 / 6.3 / 4.7° | 15.7 / 13.9 / 11.9° |

- **Pressure matters more the softer the ground.** On firm lawn it is worth
  half a degree. On typical lawn, dropping from 12 to 8 psi buys Home a
  degree. On soft ground it is worth 3°.
- **The ground matters far more than pressure.** On soft wet ground Home can
  only climb 6–8°, half its 12° rating, while the AWD Pro holds 12–16°.
  Home's rating needs a "dry ground" qualifier, or the Home needs more
  driven grip.
- **The deflection limit allows pressures down to about 3.6 psi on Home.**
  The real floor is the tyre maker's minimum, where the bead starts to slip
  on the rim, which isn't modelled.
- **Changes to earlier numbers:**
  - Home's grip limit moves from 14.1° to 14.2°, and Pro's from 21.8° to
    22.7°, because each axle's tyres now follow their own load.
  - Every check status is unchanged.
  - Rolling resistance is lower (about 0.085 at rest, was 0.10). Home's
    mowing runtime goes from 1.39 to 1.45 h, and the stock-gearing 12° climb
    needs 3.8× rated (was 4.0×).
  - The tyre springs are preloaded, so parked machines sit at their design
    heights. Without that, every deck sat 10–14 mm low.
  - The front-battery trial re-ran: today's layout now wins more clearly
    (−28.6 against −26.3), with grip 14.2° → 14.5° and still 2° of working
    slope and 11 kg lost.
  - Baselines re-ran: the lawn tractors' 20″ rear tyres at 10 psi grip to
    about 17.8°, against Home's 14.2° on 18″ golf-cart tyres at 12 psi. Same
    statuses as before.

**Caveats:**

- The Brixius equations come from 1970s–80s bias-ply tractor tyres and
  under-predict pressure effects.
- Soft ground means weak soil here, not slippery wet grass.
- Use the results to compare pressures. A pull test at two pressures would
  calibrate the model.

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
