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

**Answer:** yes, but it is a near tie with today's layout, and the gain isn't
the battery's.

- **Where the box goes:** over the front axle, on a stand that lifts it
  640 mm, clear of the steered tyres and the steering column.
- **What else has to move:**
  - the operator back over the rear axle (on a seat bridge);
  - the deck back;
  - the PTO unit 50 mm further out.
- **Gains:** grip improves from 14.1° to 14.9°, because the operator's weight
  moves onto the driven wheels. Course results are unchanged.
- **Costs:**
  - the high box lowers the static working slope from 22.7° to 20.6°;
  - the stand, the seat bridge and the longer nose add 10 kg.
- **Range limits:** three genes ended at theirs (box height, operator, deck),
  so the layout is boxed in by real parts. The steered tyres, the rear drive
  motor and the rear tyres set those limits.

A natural next trial frees the box to go anywhere. That tests whether moving
the operator back pays off on its own, with the box staying under the seat.
