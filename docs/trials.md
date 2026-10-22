# Design trials: evolving the designs

A trial asks one design question and answers it with evidence. It names:

- the design values allowed to change (**genes**);
- what to push up or down (**objectives**);
- what must stay true (**constraints**).

Then it evolves designs that answer the question.

```bash
uv run eox evolve --trial home-front-battery
```

Every candidate design gets the same scrutiny as the real one:

- the full `eox calc` engineering checks;
- the BOM;
- the [terrain course](simulation.md) in MuJoCo.

So a trial can't find a "better" design by slipping past a check the repo
enforces. Where a trial found a loophole, the loophole became a check. The
first trial added three:

- the steered front tyres must clear every part, lock to lock;
- the power box must sit on the frame;
- the steering column must clear the box.

## Writing a trial

A trial is a file in `design/trials/<name>.toml`.

```toml
[trial]
name = "home-front-battery"
model = "home"
question = "Can the Home carry its battery box at the front ...?"
course_configs = ["deck"]      # course runs per design: "deck", "bare" or both
population = 14
generations = 20
seed = 1

[[trial.gene]]                 # a design value the trial may change
key = "layout.powerbox_x"      # dotted key, as in [overrides]; list items by index ("layout.operator_cg.0")
min = 1250
max = 2300
step = 10
why = "box centre: over the front axle, or hung out ahead of it"

[[trial.gene]]
key = "deck.pto_unit_y"
choices = [430, -430, 480, -480]

[[trial.objective]]            # score += weight x metric / scale (negated for "max"); lowest score wins
metric = "grip_limit_deg"
goal = "max"
weight = 3
scale = 1

[[trial.constraint]]           # breaking one loses to every design that doesn't
metric = "calc_fails"
max = 0
```

Tyre pressures can be genes too: `axle.tire_pressure_kpa` and
`steer_axle.tire_pressure_kpa`. So can the ground: `ground.cone_index_kpa`
runs the whole trial on firmer or softer turf.

**Metrics** (defined in `src/eox/evolve/evaluate.py`):

| Group | Metrics |
|---|---|
| Checks | `calc_fails`, `calc_warns` |
| Course | `course_fails`, `course_warns`, `wheel_lift_s`, `deck_float_mm`, `side_slope_wheel_n`, `course_peak_torque_s`, `course_energy_wh` |
| Machine | `mass_kg`, `cost_usd`, `mowing_runtime_h` |
| Slopes | `working_slope_deg`, `grip_limit_deg`, `rated_slope_deg`, `climb_torque_x` |

## How it evolves

- **Starting population:** today's design, plus random designs inside the
  gene ranges. If today's design lies outside the ranges, it is still
  evaluated, as the reference.
- **Each generation:** the best two designs pass through unchanged. The rest
  are bred by tournament selection, uniform crossover and mutation. Mutation
  is a step of about 20 % of each gene's range, shrinking to half that by the
  last generation.
- **Ranking:** feasible first. A design that breaks a constraint loses to
  every design that doesn't. Among feasible designs, the lowest score wins.
- **Determinism:** the random generator is seeded, and every evaluation is
  cached in `trials/<name>/history.jsonl`.
  - Re-running a trial replays it from the cache in a fraction of a second.
  - `--generations 30` extends a run, evaluating only the new designs.
  - `--fresh` starts over. Use it after the model changes, since cached
    scores are then stale.
- **Speed:** a design takes about 9 s (calcs plus one course run). Designs
  are evaluated in parallel on all but one CPU, so 14 × 20 designs takes
  about 8 minutes on 8 cores.

## Outputs

`trials/<name>/` holds:

- **`report.md`:** the answer (best design against today's), the genes with
  any that ended at a range limit, the leaderboard, and the objectives.
- **`best.toml`:** the best design's changed values as `[overrides]`.
- **`progress-*.svg`:** the score of every design by generation.
- **`history.jsonl`:** every evaluation, which is the cache.

**A trial is evidence, not a decision.** To adopt a result:

1. Read the report.
2. Edit `design/models/<model>.toml` in a pull request.
3. Re-run `eox all`.

`tests/test_evolve.py` re-evaluates the committed `best.toml` of each trial
it knows, so a later model change that breaks a published result shows up.

## Trial: home-front-battery

**Question:** can the Home carry its battery box at the front, the way a
tractor carries its engine? [Report](../trials/home-front-battery/report.md)

**Answer:** it can, but today's layout scores better (−28.6 against −26.3),
and the small gain isn't the battery's.

- **Where the box goes:** over the front axle, on a stand that lifts it
  650 mm, clear of the steered tyres and the steering column.
- **What else has to move:**
  - the operator back over the rear axle (on a seat bridge);
  - the deck back;
  - the PTO unit 50 mm further out.
- **Gains:** grip improves only from 14.2° to 14.5°, because the operator's
  weight moves onto the driven wheels. Course results are unchanged.
- **Costs:**
  - the high box lowers the static working slope from 22.7° to 20.6°;
  - the stand, the seat bridge and the longer nose add 11 kg.
- **Range limits:** three genes ended at theirs (box height, operator, deck),
  so the layout is boxed in by real parts. The steered tyres, the rear drive
  motor and the rear tyres set those limits.

A natural next trial frees the box to go anywhere. That tests whether moving
the operator back pays off on its own, with the box staying under the seat.

## Trial: home-layout

**Legacy experiment:** deliberately stopped during generation 15 after 14
completed generations when the scope was corrected to a fabricated steel
kit. It holds donor axle envelopes fixed and does not optimize chassis
sections or joints. The [steel chassis study](steel-chassis.md) is the
starting point for the next structural search.

The Home-first search keeps the pack low and tests wheelbase, battery and
operator positions, deck position and PTO side, and a pivoting front axle.
It runs both bare and deck-fitted configurations for every candidate.

```bash
uv run eox evolve --trial home-layout --workers 16 --fresh
```

The configured search is 64 designs for 30 generations, with four elites and
seed 1. Up to 1,920 population slots are considered; elites and repeated
designs are cached, so the number of distinct evaluations is lower.

The score prioritizes course warnings and wheel lift, then balances deck
clearance, grip, static stability and mass. Feasible candidates must have no
calculation or rated-course failures, at least 14 degrees of modelled grip
limit, at least 17 degrees of the static half-tip metric, at least 1.4 hours
of predicted mowing runtime, and no more than 310 kg with the deck. These
are search constraints, not validated operating ratings; the existing
1.5-hour runtime target remains unchanged.

Gearing stays at Home's 15:1 ratio. Extra reductions are excluded until their
geometry, mass and cost are represented. The battery height, tyre pressures,
soil properties, motor ratings, efficiencies, and operating-slope targets
are fixed. The pivot option uses the existing 10-degree roll stop; its
mounting hardware and any mass/cost difference still need detailed design.

The current pivot option also retains vertical spring travel in the dynamic
model. A conventional donor beam on a fixed frame cradle requires a separate
roll-only configuration; see [front-axle research](research/home-front-axle.md).
Treat this search as exploratory until its winners are rechecked with that
configuration and measured donor geometry.

Before adopting a result, compare it with H0 and with H0 plus only the axle
pivot. Recheck promising layouts with different operator masses and ground
strengths, and verify the full terrain course and clearances independently.
Keep the original model unchanged until the result has been reviewed.

Use [ML2](remote-simulation.md) for larger runs. Keep long jobs in `tmux`,
use a separate source snapshot for each experiment, and preserve the new
trial file and its checksum alongside the source commit and dependency lock.
## Active kit layout study: `home-kit-front`

Launched on ML2 on 2026-10-22 at 17:14 EDT. Configuration:
[`design/trials/home-kit-front.toml`](../design/trials/home-kit-front.toml),
model [`home-kit`](../design/models/home-kit.toml): 96 designs × 40
generations, seed 22, 16 workers, both bare and deck-fitted courses.

This is a new layout surrogate for concept B, not a restart of the stopped
donor-envelope search. It regenerates the three layer inventories, steel
masses and 56 × 34 in blank-envelope nests as frame length changes. It keeps
the battery in front and uses a front roll pivot without a vertical
suspension joint. The full B0 battery/distribution enclosure is retained as
a conservative envelope/mass allowance, in addition to the steel body layers.
Rear reduction/differential/brakes retain a generic 45 kg allowance, with
ideal open-differential actuation; no donor assembly is selected.

Body-layer CGs are coarse point estimates and full body surfaces are not
collision-tested. A below-battery steering linkage/column route is a
packaging hypothesis, not a solved linkage. The study does not validate
fabricated joints, chassis stiffness, bearing interfaces or the new kit's
cost. The reported purchased-parts budget is a legacy proxy, not a quote.

Baseline before evolution: no engineering-check or course failures;
327.6 kg deck-fitted machine mass excluding operator, grip limit 13.5°,
static working-slope screening metric 17.2°, estimated mowing runtime 1.38 h,
0.70 s summed wheel lift across both courses and about 108 mm required deck
float. The course warning is deck float over the twist. These are surrogate
predictions, not measured operating capabilities. The search's runtime
screening floor is 1.3 h; the product target remains 1.5 h, its normal
engineering warning is preserved, and runtime remains an objective.

The new narrow front tyres exposed inconsistent transverse versus axial
wheel inertia in MJCF generation. The transverse estimate now uses the same
radial mass distribution as the axial estimate. Older models retain their
leaf-spring configuration. All 109 local tests passed, including kit mass
conservation, model compilation and settled axle loads. Old evaluation
caches must not be reused after this physics change.

Remote snapshot: `/home/ml2/eox-sim/home-kit-front-km5GND`.
Tmux session: `eox-kit-front-km5GND`. It contains the working-tree source
snapshot, base commit and per-file SHA256 manifest, job script, preflight
log and fresh trial cache. Local provenance is in `out/ml2-kit-front/`.
The source snapshot includes uncommitted changes; it is not described as an
unmodified checkout of its base commit.

```sh
ssh ml2@ml2.anceralabs.com 'cd /home/ml2/eox-sim/home-kit-front-km5GND && .venv/bin/python status.py'
```

The status helper reads progress and writes a checkpoint without restarting
the optimizer. Review winners and timestep sensitivity before adopting any
values. Results have not yet been adopted into a recommended design.
