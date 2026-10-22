# Trial: home-front-battery

**Question.** Can the Home carry its battery box at the front, like a tractor's engine, and keep its 12 deg climb, its stability and its course results?

Generated 2026-10-19 by `uv run eox evolve --trial home-front-battery` from `design/trials/home-front-battery.toml`: 14 designs x 20 generations, seed 1; 242 distinct designs evaluated (97 feasible), 62 CPU-minutes. Each design runs the full `eox calc` checks and the terrain course (deck).

## Answer: the best design against today's

| Metric | Today | Best | |
|---|---|---|---|
| steepest climb on grip, deck fitted | 14.2 | **14.5** | deg |
| motor torque on the rated climb, deck fitted | 3.17 | **3.26** | x rated |
| max working slope (half the lowest static tip angle) | 22.7 | **20.6** | deg |
| course obstacles that WARN | 2 | **2** |  |
| longest wheel lift, summed over the obstacles | 2.46 | **2.5** | s |
| float the deck's hitch needs (worst obstacle) | 108 | **108** | mm |
| lightest wheel load on the side slope | 0.03 | **0.02** | N |
| machine mass with the deck, no operator | 302 | **313** | kg |
| purchased parts, budgetary | 3,714 | **3,714** | $ |
| runtime on one charge, mowing | 1.45 | **1.44** | h |
| engineering checks that FAIL | 0 | **0** |  |
| engineering checks that WARN | 4 | **4** |  |
| course obstacles that FAIL (stuck, rolled, left the course) | 0 | **0** |  |

**Score** (lower is better): today -28.61; best -26.33.

| Gene | Why | Range | Today | Best |
|---|---|---|---|---|
| `layout.powerbox_x` | box centre: over the front axle, or hung out ahead of it | 1250 to 2300 | 510 | **1400** |
| `layout.powerbox_z` | box underside: on the nose rails, or on a stand clear of the steered tyres | 340 to 650 | 230 | **650** (range limit) |
| `layout.front_overhang` | a longer nose to hang the box out front (rail mass follows length) | 250 to 900 | 250 | **390** |
| `layout.operator_cg.0` | operator fore-aft: back over the rear axle puts weight on the driven tyres | 150 to 700 | 520 | **150** (range limit) |
| `deck.x_center` | mid-mount deck fore-aft, between the rear tyres and the steered tyres | 560 to 1060 | 800 | **560** (range limit) |
| `deck.pto_unit_y` | where the PTO unit stands: either side, 50 mm further out clears a floor pan above it | 430 / -430 / 480 / -480 | 430 | **480** |

At a range limit: `layout.powerbox_z`, `layout.operator_cg.0`, `deck.x_center`. The best value may lie beyond it; widen the range if the design allows, or treat the limit as a real constraint.

Course warnings on the best design: deck twist: front L wheel lifts 0.9 s; deck needs 108 mm of float (has 75); deck side slope 17 deg: front L wheel lifts 1.6 s.

## Leaderboard

| # | Score | `powerbox_x` | `powerbox_z` | `front_overhang` | `operator_cg.0` | `x_center` | `pto_unit_y` | Grip | Working slope | Course WARN | Mass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | -26.33 | 1400 | 650 | 390 | 150 | 560 | 480 | 14.5 | 20.6 | 2 | 313 |
| 2 | -26.26 | 1400 | 630 | 300 | 160 | 610 | 480 | 14.4 | 20.7 | 2 | 312 |
| 3 | -26.21 | 1410 | 610 | 390 | 150 | 560 | 480 | 14.4 | 20.8 | 2 | 313 |
| 4 | -26.19 | 1400 | 630 | 350 | 150 | 610 | 480 | 14.4 | 20.7 | 2 | 312 |
| 5 | -26.17 | 1400 | 630 | 370 | 150 | 610 | 480 | 14.4 | 20.7 | 2 | 312 |
| 6 | -26.15 | 1450 | 610 | 350 | 150 | 560 | -480 | 14.4 | 20.8 | 2 | 312 |
| 7 | -26.15 | 1410 | 620 | 390 | 150 | 590 | 480 | 14.4 | 20.7 | 2 | 313 |
| 8 | -26.09 | 1430 | 630 | 390 | 150 | 560 | 480 | 14.4 | 20.7 | 2 | 313 |
| 9 | -26.07 | 1410 | 630 | 390 | 150 | 560 | 480 | 14.4 | 20.7 | 2 | 313 |
| 10 | -26.07 | 1400 | 650 | 390 | 160 | 560 | 480 | 14.4 | 20.6 | 2 | 313 |

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
