# Trial: home-front-battery

**Question.** Can the Home carry its battery box at the front, like a tractor's engine, and keep its 12 deg climb, its stability and its course results?

Generated 2026-10-19 by `uv run eox evolve --trial home-front-battery` from `design/trials/home-front-battery.toml`: 14 designs x 20 generations, seed 1; 241 distinct designs evaluated (45 feasible), 52 CPU-minutes. Each design runs the full `eox calc` checks and the terrain course (deck).

## Answer: the best design against today's

| Metric | Today | Best | |
|---|---|---|---|
| steepest climb on grip, deck fitted | 14.1 | **14.9** | deg |
| motor torque on the rated climb, deck fitted | 3.33 | **3.4** | x rated |
| max working slope (half the lowest static tip angle) | 22.7 | **20.6** | deg |
| course obstacles that WARN | 2 | **2** |  |
| longest wheel lift, summed over the obstacles | 3.68 | **3.58** | s |
| float the deck's hitch needs (worst obstacle) | 107 | **105** | mm |
| lightest wheel load on the side slope | 0 | **0** | N |
| machine mass with the deck, no operator | 302 | **312** | kg |
| purchased parts, budgetary | 3,714 | **3,714** | $ |
| runtime on one charge, mowing | 1.39 | **1.37** | h |
| engineering checks that FAIL | 0 | **0** |  |
| engineering checks that WARN | 4 | **5** |  |
| course obstacles that FAIL (stuck, rolled, left the course) | 0 | **0** |  |

**Score** (lower is better): today -27.09; best -26.55.

| Gene | Why | Range | Today | Best |
|---|---|---|---|---|
| `layout.powerbox_x` | box centre: over the front axle, or hung out ahead of it | 1250 to 2300 | 510 | **1370** |
| `layout.powerbox_z` | box underside: on the nose rails, or on a stand clear of the steered tyres | 340 to 650 | 230 | **640** (range limit) |
| `layout.front_overhang` | a longer nose to hang the box out front (rail mass follows length) | 250 to 900 | 250 | **290** |
| `layout.operator_cg.0` | operator fore-aft: back over the rear axle puts weight on the driven tyres | 150 to 700 | 520 | **150** (range limit) |
| `deck.x_center` | mid-mount deck fore-aft, between the rear tyres and the steered tyres | 560 to 1060 | 800 | **560** (range limit) |
| `deck.pto_unit_y` | where the PTO unit stands: either side, 50 mm further out clears a floor pan above it | 430 / -430 / 480 / -480 | 430 | **480** |

At a range limit: `layout.powerbox_z`, `layout.operator_cg.0`, `deck.x_center`. The best value may lie beyond it; widen the range if the design allows, or treat the limit as a real constraint.

Course warnings on the best design: deck twist: front L wheel lifts 1.2 s; deck needs 105 mm of float (has 75); deck side slope 17 deg: front L wheel lifts 2.2 s.

## Leaderboard

| # | Score | `powerbox_x` | `powerbox_z` | `front_overhang` | `operator_cg.0` | `x_center` | `pto_unit_y` | Grip | Working slope | Course WARN | Mass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | -26.55 | 1370 | 640 | 290 | 150 | 560 | 480 | 14.9 | 20.6 | 2 | 312 |
| 2 | -26.53 | 1370 | 650 | 290 | 150 | 560 | 480 | 14.9 | 20.6 | 2 | 312 |
| 3 | -26.35 | 1370 | 640 | 310 | 150 | 560 | 480 | 14.8 | 20.7 | 2 | 312 |
| 4 | -26.29 | 1370 | 650 | 250 | 150 | 590 | 480 | 14.8 | 20.6 | 2 | 311 |
| 5 | -26.29 | 1390 | 650 | 290 | 150 | 560 | 480 | 14.8 | 20.6 | 2 | 312 |
| 6 | -26.27 | 1370 | 650 | 330 | 150 | 560 | -480 | 14.8 | 20.6 | 2 | 312 |
| 7 | -26.27 | 1370 | 620 | 330 | 150 | 560 | 480 | 14.8 | 20.7 | 2 | 312 |
| 8 | -26.25 | 1370 | 650 | 290 | 150 | 590 | 480 | 14.8 | 20.6 | 2 | 312 |
| 9 | -26.23 | 1370 | 650 | 250 | 150 | 590 | -480 | 14.8 | 20.6 | 2 | 311 |
| 10 | -26.21 | 1370 | 650 | 310 | 150 | 590 | 480 | 14.8 | 20.6 | 2 | 312 |

## Progress

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="progress-dark.svg">
  <img alt="Score of every design by generation, and the best so far" src="progress-light.svg" width="100%">
</picture>

## Adopting

`best.toml` lists the best design's changed values as `[overrides]` for `design/models/home.toml`. A trial is evidence for a decision, not the decision: review the numbers above, then edit the model file in a pull request, so the change and its reasons are recorded.

Objectives and constraints:

- max `grip_limit_deg` (steepest climb on grip, deck fitted), weight 3 per 1 deg
- max `working_slope_deg` (max working slope (half the lowest static tip angle)), weight 1 per 1 deg
- min `course_warns` (course obstacles that WARN), weight 2 per 1 
- min `wheel_lift_s` (longest wheel lift, summed over the obstacles), weight 1 per 1 s
- min `mass_kg` (machine mass with the deck, no operator), weight 1 per 10 kg
- constraint: `calc_fails` <= 0
- constraint: `course_fails` <= 0
