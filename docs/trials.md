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

More options:

- **`cap`:** an objective can stop paying past a value. For example,
  `metric = "steer_margin"` with `cap = 0.40` earns credit for steering
  margin up to 40 %; beyond that, the other objectives (a smaller cylinder,
  lower pump draw) decide. Without a cap, "more is better" can win trivially.
  The first `pro-steering` run chose the biggest cylinder at the highest
  pressure.
- **`patience`:** the trial stops after this many generations without a better
  design (default 8; 0 runs them all).
- **`[trial.overrides]`:** values fixed for every design in the trial, such as
  `"ground.cone_index_kpa" = 200` for soft wet ground.
- **`--lod low|medium`:** runs the trial's course at a cheaper level of detail
  ([simulation.md](simulation.md#levels-of-detail)). Results go to
  `trials/<name>@<lod>/`.
- **Several `--trial` flags** run a series, one after another. Wrap a long
  series in `caffeinate -is` on a Mac so it doesn't sleep.

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

## Is a cheaper level of detail good enough?

`uv run eox fidelity --trial <name> --lod low` compares a trial run at low (or
medium) detail with its full-detail run. Each run's top designs are scored
again at the other level, and `trials/<name>@<lod>/fidelity.md` reports:

- **Improvement captured:** how much of the full run's gain over today's
  design the cheap run's best achieves, scored at full detail. Read this
  first.
- **Rank agreement and top-10 overlap:** whether both levels order the
  designs the same way. When the top designs score almost the same, their
  order is noise at either level, and the report says so.
- **The genes of the two bests, side by side.**

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

## Other trials

| Trial | Question | Answer |
|---|---|---|
| [`home-pivot-axle`](../trials/home-pivot-axle/report.md) | Should Home's front axle pivot? | Yes: a stop of 15° or more. Wheel lift 5.8 s → 0.1 s. Working slope 22.7° → 19.8°. |
| [`home-15-degrees`](../trials/home-15-degrees/report.md) | What would a 15° rating take? | 8 psi drive tyres, the deck back, the PTO unit out, 15:1 gears. Rated 15.5° with a thin torque margin. |
| [`home-layout-free`](../trials/home-layout-free/report.md) | Best Home layout, battery anywhere? | The battery stays low under the seat; move the deck back. |
| [`home-wet-ground`](../trials/home-wet-ground/report.md) | Home on soft wet ground? | No setup clears the kerb. The best reaches 8.1° of grip; soft ground needs driven front wheels. |
| [`pro-steering`](../trials/pro-steering/report.md) | Size the Pro's steering cylinder | Keep 45 mm and 4 L/min. Relief 110 bar, lever arm 140 mm. Margin 12 → 44 %. |

Low-detail runs of `home-pivot-axle` and `home-15-degrees`
(`trials/<name>@low/`, with `fidelity.md`) reached the same decisions in less
than half the time. See the [design log](design-log.md).
