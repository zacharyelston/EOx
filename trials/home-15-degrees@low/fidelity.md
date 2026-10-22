# Fidelity: `home-15-degrees` at low detail against high

Generated 2026-10-21 by `uv run eox fidelity --trial home-15-degrees --lod low`. Each run's top 10 designs were scored again at the other level.

| Measure | Value | Reading |
|---|---|---|
| **Improvement captured** (the low run's best, scored at high) | **100.0 %** | of high's improvement over today's design (19.20 points) |
| Rank agreement (Spearman, 19 designs feasible at both levels) | 0.67 | 1 = same order |
| Top-10 overlap | 0 of 10 | designs both runs rank in their top 10 |
| Regret: the low run's best, scored at high, minus high's best | 0.00 | 0 = same answer; score spread across these designs is 0.58 |
| Feasibility flips | 1 | designs that pass at one level and fail at the other |

The top designs score within 0.58 of each other, under 3 % of the improvement: their order is noise at either level, so rank agreement and overlap say little here. Read the improvement captured and the genes the two bests share.

| Gene | High's best | Low's best |
|---|---|---|
| `vehicle.max_slope_deg` | 15.5 | 15.5 |
| `axle.ratio` | 15 | 24.8 |
| `axle.tire_pressure_kpa` | 55 | 55 |
| `layout.operator_cg.0` | 520 | 520 |
| `layout.powerbox_x` | 510 | 510 |
| `deck.x_center` | 560 | 560 |
| `deck.pto_unit_y` | 480 | -430 |

| Design | Score at high | Score at low |
|---|---|---|
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=560, pto_unit_y=480 | -114.10 | -113.10 |
| max_slope_deg=15.5, ratio=24.8, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=560, pto_unit_y=-430 | -114.10 | -114.10 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=560, pto_unit_y=-480 | -114.10 | -113.10 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=560, pto_unit_y=430 | -114.10 | -113.10 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=600, pto_unit_y=480 | -114.00 | -113.00 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=600, pto_unit_y=-480 | -114.00 | -113.00 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=600, pto_unit_y=-430 | -114.00 | -113.00 |
| max_slope_deg=15.5, ratio=24.8, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=600, pto_unit_y=-430 | -114.00 | -114.00 |
| max_slope_deg=15.5, ratio=24.8, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=600, pto_unit_y=430 | -114.00 | -114.00 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=520, powerbox_x=510, x_center=640, pto_unit_y=-430 | -113.90 | -112.90 (fails) |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=560, pto_unit_y=430 | -113.90 | -112.90 |
| max_slope_deg=15.5, ratio=24.8, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=610, pto_unit_y=430 | -113.80 | -113.80 |
| max_slope_deg=15.5, ratio=24.8, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=610, pto_unit_y=-430 | -113.80 | -113.80 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=560, powerbox_x=520, x_center=560, pto_unit_y=430 | -113.80 | -112.80 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=610, pto_unit_y=430 | -113.80 | -112.80 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=610, pto_unit_y=-480 | -113.80 | -112.80 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=640, pto_unit_y=430 | -113.70 | -112.70 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=640, pto_unit_y=480 | -113.70 | -112.70 |
| max_slope_deg=15.5, ratio=15, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=670, pto_unit_y=-430 | -113.70 | -112.70 |
| max_slope_deg=15, ratio=24.8, tire_pressure_kpa=55, 0=540, powerbox_x=520, x_center=560, pto_unit_y=-480 | -111.40 | -111.40 |
