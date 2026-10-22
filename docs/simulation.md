# Terrain course: MuJoCo simulation

`uv run eox course --model home|pro` drives each model over a standard test
course in [MuJoCo](https://mujoco.org), bare and with the mower deck fitted,
and scores every obstacle. The physics runs in MuJoCo's C engine. Python only
builds the model, steers it at 50 Hz and reads the results. Each run takes
about 5 s for 100 s of simulated driving.

The hand calcs (`eox calc`) answer static questions: the tip angle, torque on a
slope, grip on a slope. The course answers the ones the calcs can't:

- what happens when the ground twists under a rigid frame;
- whether a kerb or a ditch stops the machine;
- how far a mounted deck would dig in;
- whether an open diff gives away grip.

## What is simulated

The MuJoCo model is generated from the same `Tractor` object the calcs and the
CAD use (`src/eox/sim/mjcf.py`). It carries exactly the reconciled masses
(`tests/test_mass.py`) and the same part envelopes.

| | Home | Pro |
|---|---|---|
| Bodies | Chassis, leaf-sprung front beam axle, two steering knuckles, four wheels | Rear half, knuckle on the roll trunnion (±10°), front half on the yaw pins, four wheels |
| Drive | One rear axle, open diff | Both axles, open diffs |
| Steering | Ackermann, rack and pinion | Hydraulic cylinder: torque-limited to the calc's 1,173 N·m, rate-limited to its 3.3 s lock to lock |
| Springs | Front leaf springs, 20 N/mm each, ±40 mm travel (REF): bounce plus ±7.6° of axle roll. With `steer_axle.oscillates = true`, the axle rolls freely on a centre pivot to ±`oscillation_max_deg` (10°) | None: the trunnion lets the halves roll |

- **Drive units:** each axle has a velocity-controlled drive, torque-limited at
  the motor's peak (4 × rated) through the axle ratio. The open diff splits
  torque equally between the two wheels.
- **Tyres:** ellipsoids (18x8.50-8). Sliding friction 0.5 on turf, plus a
  little spin-in-place friction.
- **Rolling resistance:** 0.10, applied as a force at each wheel centre. Like
  the drive calc, it uses up the driven tyres' grip.
- **Collisions:** every other part envelope collides with the ground, so
  strikes on the diff, motor, rails or box are scored.
- **The deck:** drawn but not colliding. A real deck rides on anti-scalp
  rollers, so the sim measures how far a rigidly mounted deck would dig in.
  That depth is the float its hitch must allow.
- **The driver:** follows the centreline with pure pursuit at 3 km/h and holds
  speed with integral action. If the machine gets stuck, rolls or leaves the
  course, the obstacle fails and the driver is set down past it, so every
  obstacle gets a result.

## Tyres and ground

Tyre grip and rolling resistance are worked out from each tyre's size,
pressure and load, and the ground's strength (`src/eox/tyres.py`). The calcs
and the course use the same model.

- **Deflection:** a pressed-in tyre's contact patch is an ellipse. So load =
  (pressure + carcass) × π × deflection × √(diameter × width), and the tyre's
  spring rate follows from that. In the sim, each wheel rides on that spring,
  above a stiff contact. Its settled squash matches the formula (13 mm on an
  EOX drive tyre at 12 psi).
- **Grip and rolling resistance:** these come from the Brixius equations
  (ASAE D497). Tyre size, load and deflection make up a mobility number
  against the ground's cone index. Lower pressure gives more deflection, so
  more grip and less rolling resistance, and the effect is larger on soft
  ground.
- **In the sim:** grip and rolling resistance follow each wheel's live load,
  so a lightly loaded tyre (on a climb, or across a slope) behaves like one.
- **The ground:** `design/ground.toml` sets lawn turf, cone index 400 kPa,
  chosen so an EOX drive tyre at its design pressure gives the turf values
  used before (traction about 0.5, rolling resistance about 0.09).
  - For firm dry lawn, set `ground.cone_index_kpa` to about 1000.
  - For soft wet ground, set it to about 200.
- **Pressures:**
  - **EOX:** 12 psi drive tyres and 14 psi steering tyres (REF, lawn-tractor
    practice).
  - **Real machines:** their makers' figures.
- **New checks:** each axle's tyre deflection must stay under 25 % of section
  height, and its pressure within the tyre's rating.
- **Pressure sweep:** `uv run eox tyres --model home` sweeps the drive-tyre
  pressure on firm, typical and wet lawn.

The equations are empirical, from bias-ply tractor tyres measured in the
1970s and 80s. They under-predict pressure effects. Also, soft ground here
means weak soil, not the surface slipperiness of wet grass. So compare
pressures with this model; don't read the numbers as absolutes. A pull test
on a real machine at two pressures would calibrate it.

## Levels of detail

`course.lod` picks how much physics each run gets (`design/course.toml`,
`[course.lod_levels]`). Select a level with `uv run eox course --lod low`, or
`eox evolve --lod low`. A trial at a cheaper level keeps its own results in
`trials/<name>@<lod>/`.

| Level | Physics step | Control rate | Terrain grid | Ground collisions | Run time |
|---|---|---|---|---|---|
| high (the reference) | 2 ms | 50 Hz | 5 cm | every part | 7–10 s |
| medium | 4 ms | 50 Hz | 5 cm | parts within 350 mm of the ground | 1.3–1.7× faster |
| low | 6 ms | 25 Hz | 10 cm | parts within 350 mm of the ground | 2–3.3× faster |

**Checked against high**, both models, bare and deck-fitted, all 7 obstacles
(28 results per level):

- **Medium:** every status matches but one. Pro's front deck on the kerb needs
  76 mm of float at medium against 73 mm at high, either side of the 75 mm
  allowance. Wheel lift, deck clearance and torque agree to within a few
  percent.
- **Low:** every status matches. Climbs come out harsher: at the coarser
  driver rate the wheels slip more near the grip limit. On the 15° climb,
  Home with the deck sits at peak torque for 15 s at low, against 4 s at high.
- **Faster physics settings that changed results were rejected:** fewer
  solver iterations, and a pyramidal friction cone.

Before trusting a cheap level for a trial, compare it with high using
`uv run eox fidelity` ([trials.md](trials.md)).

## The course

The course is defined in `design/course.toml`: a heightfield 84.7 m long and
8 m wide on a 5 cm grid.

| # | Obstacle | Size | Tests |
|---|---|---|---|
| 1 | bump | 75 mm × 0.6 m half-cosine | Impact, pitch |
| 2 | kerb | 75 mm step up, 3 m, step down | Pushing the front wheels up a step |
| 3 | ditch | 200 mm deep, 2 m swale | Break-over and approach clearance |
| 4 | twist | Three 150 mm humps, alternating under the left and right wheel tracks | Frame twist: suspension, trunnion, wheel lift |
| 5 | climb 12° | 1 m rise, rounded crests | The Home's rated climb |
| 6 | climb 15° | 1 m rise | The Pro's rated climb. Above the Home's rating, so its result is INFO for the Home. |
| 7 | side slope 17° | Tilts in over 4 m, holds 8 m, tilts out | The cross-slope label value, and the twist at each end |

**Scoring:**

- **FAIL:** stuck, rolled over, or left the course.
- **WARN:** any of these:
  - a wheel off the ground for 0.3 s or more;
  - a part striking the ground;
  - the deck needing more than 75 mm of float;
  - a motor at its torque limit for more than 3 s.
- **INFO:** an obstacle beyond the model's rating.

## Checks against the hand calcs

- **Static loads:** parked on the flat, the simulated axle loads match
  `Tractor.axle_loads_n` to within 2 %, for both models, bare and deck-fitted
  (`tests/test_course.py`).
- **Grip on a climb:**
  - The calc puts Home's grip limit with the deck at 14.2° on turf.
  - On a long ramp, the sim climbs 12° at speed, slips at 13°, and crawls
    with wheelspin at 14–15°.
  - The calc assumes both rear tyres reach full grip together. The open diff
    sends equal torque to both wheels, so the lighter wheel sets the limit.
  - The two agree within about a degree.

## Results (deck fitted)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/home-course-dark.svg">
  <img alt="EOX Home course results" src="img/home-course-light.svg" width="100%">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/pro-course-dark.svg">
  <img alt="EOX Pro course results" src="img/pro-course-light.svg" width="100%">
</picture>

**EOX Home: 0 FAIL, 2 WARN.**

- **Rated 12° climb:** clears it with the deck, at 3.5× rated motor torque.
  On a long 13° ramp it starts to slip. That is little margin.
- **15° climb:** above its rating (INFO). It crawls up at peak torque with the
  wheels spinning.
- **Front axle twist:** the leaf-sprung beam axle runs out of roll travel
  (±7.6° REF) on the twist and at both ends of the side slope, and a front
  wheel lifts for 1–2.5 s.
- **Steady 17° side slope:** all four wheels stay loaded, with about 400 N on
  the uphill front tyre.
- **Possible fix:** a pivoting front axle, as most lawn tractors have, would
  keep the front wheels down.
- **Kerb:** clears, but the rear wheels spin hard pushing the front tyres up
  it. Rigid tyres make this pessimistic.

**EOX Pro: 0 FAIL bare; 4 WARN with the deck, all about the deck.**

- **Bare:** clears every obstacle. The trunnion uses 9° of its ±10° on the
  twist, and no wheel lifts. On the 17° side slope the lightest wheel still
  carries about 550 N.
- **With the deck:** a rigidly mounted front deck would dig 130–310 mm into
  the climbs, the twist and the ditch. The front-deck coupling has to pivot,
  not just float 75 mm (open as
  [issue 7](https://github.com/zacharyelston/EOx/issues/7)).

## Limits of the model

- **Rigid tyres:** they don't wrap around a kerb edge, so kerbs and bumps come
  out harsher than real.
- **Flat friction:** one coefficient (0.5) for all of turf. Tyres have no slip
  curve.
- **REF values:** the leaf-spring rate and travel, the trunnion damping and the
  spin friction are REF.
- **Driving style:** slow, steady driving at 3 km/h. It doesn't test braking,
  tight turns on slopes, or rollover at speed.
- **The deck:** carried rigidly and judged by how far it would dig in, not by
  a model of its hitch.

## Outputs and viewing

| Output | Where |
|---|---|
| Report per model | `out/<model>-course.md` |
| Figure (light + dark) | `docs/img/<model>-course-*.svg` |
| Frames (`--render`) | `docs/img/<model>-course.png` |
| Video (`--video`) | `out/sim/<model>-<config>.mp4`, or `.gif` without ffmpeg |
| MuJoCo model | `out/sim/<model>-bare.xml`, `-deck.xml` (+ `.hfield.bin`) |

The live viewer opens MuJoCo's window and drives the course in real time. Drag
to orbit; the chase camera is under *Rendering → Camera*.

```bash
uv run eox course --model pro --view
```

The exported XML opens in MuJoCo's own `simulate` app (passive; it doesn't
include the driver).
