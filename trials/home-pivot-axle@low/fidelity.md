# Fidelity: `home-pivot-axle` at low detail against high

Generated 2026-10-21 by `uv run eox fidelity --trial home-pivot-axle --lod low`. Each run's top 10 designs were scored again at the other level.

| Measure | Value | Reading |
|---|---|---|
| **Improvement captured** (the low run's best, scored at high) | **99.6 %** | of high's improvement over today's design (24.17 points) |
| Rank agreement (Spearman, 20 designs feasible at both levels) | -0.67 | 1 = same order |
| Top-10 overlap | 0 of 10 | designs both runs rank in their top 10 |
| Regret: the low run's best, scored at high, minus high's best | 0.11 | 0 = same answer; score spread across these designs is 0.24 |
| Feasibility flips | 0 | designs that pass at one level and fail at the other |

The top designs score within 0.24 of each other, under 1 % of the improvement: their order is noise at either level, so rank agreement and overlap say little here. Read the improvement captured and the genes the two bests share.

| Gene | High's best | Low's best |
|---|---|---|
| `steer_axle.oscillates` | true | true |
| `steer_axle.oscillation_max_deg` | 15 | 15 |
| `steer_axle.spring_travel` | 65 | 35 |
| `steer_axle.spring_rate_n_per_mm` | 24 | 32 |

| Design | Score at high | Score at low |
|---|---|---|
| oscillates=true, oscillation_max_deg=15, spring_travel=65, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=55, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=40, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=80, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=30, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=50, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=75, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=45, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=60, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=70, spring_rate_n_per_mm=24 | -21.41 | -17.83 |
| oscillates=true, oscillation_max_deg=15, spring_travel=35, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=15, spring_travel=45, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=15, spring_travel=40, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=15, spring_travel=50, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=15, spring_travel=65, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=15, spring_travel=55, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=15, spring_travel=30, spring_rate_n_per_mm=32 | -21.30 | -19.57 |
| oscillates=true, oscillation_max_deg=14, spring_travel=65, spring_rate_n_per_mm=30 | -20.77 | -19.31 |
| oscillates=true, oscillation_max_deg=14, spring_travel=50, spring_rate_n_per_mm=30 | -20.77 | -19.31 |
| oscillates=true, oscillation_max_deg=14, spring_travel=30, spring_rate_n_per_mm=38 | -20.58 | -19.39 |
