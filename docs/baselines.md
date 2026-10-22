# Baselines: EOX against real machines

Generated 2026-10-19 by `uv run eox baseline`. Every machine runs the same static checks (tip angle, grip) and the same terrain course (85 m, 7 obstacles, deck fitted, turf). Real machines are modelled from their published specs in `design/reference/`; what the makers don't publish (weight split, CG height) is estimated and marked REF there. Each machine is scored against its own rated slope.

| Machine | Type | Mass (kg) | Price ($) | Rated climb / across | Grip limit | Working slope | Front axle share (with operator) | Mowing runtime | Course |
|---|---|---|---|---|---|---|---|---|---|
| EOX Home | EOX, electric, 2WD | 302 | 3,714 | 12 / 17 deg | 14.2 deg | 23.9 deg | 36 % | 1.4 h | 0 FAIL, 2 WARN, 4 PASS, 1 INFO |
| EOX Pro | EOX, electric, articulated AWD | 371 | 5,338 | 15 / 17 deg | 22.7 deg | 20.2 deg | 58 % | 1.3 h | 0 FAIL, 4 WARN, 3 PASS |
| Cub Cadet XT1 LT42 | gas lawn tractor, 547 cc, hydrostatic, 2WD | 236 | 2,399 | 15 / 15 deg | 17.8 deg | 12.7 deg | 35 % | gas | 0 FAIL, 1 WARN, 5 PASS, 1 INFO |
| John Deere X350 | gas lawn tractor, 21.5 hp, hydrostatic, 2WD | 248 | 3,950 | 15 / 15 deg | 17.8 deg | 13.2 deg | 36 % | gas | 0 FAIL, 1 WARN, 5 PASS, 1 INFO |
| Husqvarna R 316TX AWD | gas articulated rider, 9.6 kW, hydrostatic AWD, front deck | 287 | 10,000 | 10 / 10 deg | 21.7 deg | 13.9 deg | 37 % | gas | 0 FAIL, 3 WARN, 1 PASS, 3 INFO |
| Ryobi 80V 42 in (RYRM8060) | electric lawn tractor, 80 V, 3 x 10 Ah, 2WD | 253 | 4,999 | 15 / 15 deg | 17.2 deg | 13.6 deg | 34 % | 1.1 h | 0 FAIL, 1 WARN, 5 PASS, 1 INFO |

Mass is with the deck, without the operator. Price: EOX = purchased parts (budgetary); real machines = list price when checked. Grip limit: the steepest climb the driven tyres hold on turf (traction 0.5), deck fitted, as `eox calc` computes it. Working slope: half the lowest static tip angle, deck fitted (`eox calc` also checks EOX without its deck, which can be lower).

## Course, obstacle by obstacle

| Machine | bump | kerb | ditch | twist | climb 12 deg | climb 15 deg | side slope 17 deg |
|---|---|---|---|---|---|---|---|
| EOX Home | PASS: pitch 3 deg | PASS: pitch 4 deg | PASS: pitch 7 deg | WARN: front L wheel lifts 0.9 s | PASS: motor 3.5x rated | INFO: motor at peak torque 4.1 s | WARN: front L wheel lifts 1.5 s |
| EOX Pro | PASS: pitch 4 deg | PASS: pitch 5 deg | WARN: deck needs 311 mm of float (has 75) | WARN: deck needs 148 mm of float (has 75) | WARN: deck needs 127 mm of float (has 75) | WARN: deck needs 159 mm of float (has 75) | PASS: lightest wheel 636 N |
| Cub Cadet XT1 LT42 | PASS: pitch 4 deg | PASS: pitch 5 deg | PASS: pitch 10 deg | WARN: deck needs 107 mm of float (has 75) | PASS: motor 3.2x rated | PASS: motor 3.7x rated | INFO: lightest wheel 388 N |
| John Deere X350 | PASS: pitch 4 deg | PASS: pitch 5 deg | PASS: pitch 9 deg | WARN: deck needs 107 mm of float (has 75) | PASS: motor 3.2x rated | PASS: motor 3.7x rated | INFO: lightest wheel 424 N |
| Husqvarna R 316TX AWD | PASS: pitch 6 deg | WARN: deck needs 93 mm of float (has 75) | WARN: deck needs 376 mm of float (has 75) | WARN: deck needs 189 mm of float (has 75) | INFO: deck needs 119 mm of float (has 75) | INFO: deck needs 145 mm of float (has 75) | INFO: lightest wheel 355 N |
| Ryobi 80V 42 in (RYRM8060) | PASS: pitch 4 deg | PASS: pitch 5 deg | PASS: pitch 9 deg | WARN: deck needs 107 mm of float (has 75) | PASS: motor 3.2x rated | PASS: motor 3.7x rated | INFO: lightest wheel 396 N |

Sources: each machine's file in `design/reference/` lists where every published number comes from.

