# Component candidates: battery, motor, controller

> **Status (power box rev B0, EOX Pro P0):** written for power box rev A1,
> when the box carried its own 2 kW motor and the pack needed 100 A.
> - **Motor and controller sections: superseded.** EOX now uses 48 V AC
>   golf-cart motor + controller "3 HP units" on the axle modules (see
>   [architecture](architecture.md)).
> - **Battery section: still relevant**, but the pack must now carry
>   ≥ 200 A continuous / 400 A peak (`Bus` checks). Re-check B1–B3 against
>   that.

Research date: 2026-10-18. Prices are what the linked page showed that day and
change often. This file only **proposes** values. `design/powerbox.toml` keeps
its REF envelopes until someone picks parts and edits it.

**How the numbers were checked.** Every candidate was run through the real
`eox calc` checks against **rev A1**: the bulkhead, the sealed battery bay and
the fan-vented motor bay. The runs used a scratch copy of the TOML with only
that candidate's keys changed; the repo file was not touched. "UNKNOWN" means
no manufacturer document gave the number, and no number here is estimated
unless it says *derived*.

## At a glance

| Part | Recommended | Price seen | Status |
|---|---|---|---|
| Battery | **Himax LAF48100** (retail as CHINS LAF48100) | $799 | Fits the REF envelope. BMS over-voltage behaviour is proven in an IEC 62619 test report. **The CB certificate number has not been found, and pack propagation was not tested.** |
| Motor | **BLDC.com DH130BLD2300**, 48 V | $752 | The only candidate whose face fits the 150 mm tray wall. IP65, Halls. Efficiency is only a vendor claim. |
| Controller | **Kelly KLS7215ND** | $139 | Small enough for the −y wall. Sine/FOC, Hall input, IP66. Battery-current setting needs confirming in amps. |

With this trio, `eox calc` gives **1 FAIL** (the doubler edge distance, a layout
detail) and 3 WARN. With `tray_height = 160` and `floor_clearance = 15` it gives
**0 FAIL** and 2 WARN. Details are in [Recommended set](#recommended-set).

## What the parts have to meet

| Part | Requirement | Why |
|---|---|---|
| Battery | 16S LiFePO4, 51.2 V, ~100 Ah, one pack | `[battery]`; the runtime check |
| Battery | BMS ≥ 100 A continuous, ≥ 100 A short-term | `continuous current` check; the controller battery limit is 100 A |
| Battery | BMS cell over-voltage trip **< 3.75 V**, target ≤ 3.70 V | S-01: 16 × 3.75 V = 60.0 V, the SELV ceiling under a charger fault |
| Battery | Charging blocked below 0 °C and above ~45–50 °C | D-06; `pack temp, parked in sun while charging` |
| Battery | **UL 2271** or **IEC 62619** for the pack, not UL 1973 or "UL-certified cells" | S-02. Packs over 1 kWh must also pass single-cell-failure propagation |
| Battery | Fits the [envelope below](#battery-envelope) | Cover blank vs the 44 in bend limit |
| Motor | 48 V BLDC/PMSM, rated torque ≥ 6.2 N·m at 40:1, peak ≥ 15 N·m | `motor torque to climb 15 deg`, grade start |
| Motor | Reaches 8 km/h | `motor speed at 8 km/h`; the 40:1 ratio is not frozen (the drivetrain is module 2) |
| Motor | Face flange + spigot that fit the 150 mm tray wall; keyed shaft for an 11T #40 sprocket; Halls | PB-101 / PB-103 hole checks |
| Motor | IP65+ | D-07: the motor bay is a wet zone |
| Controller | 48 V sine/FOC, Hall input, programmable battery limit ≥ 100 A, tolerates ~60 V | `controller battery limit vs pack peak`; BMS trip voltage |
| Controller | Inputs for key, seat, brake, fwd/rev, throttle | S-07 |
| Controller | IP65+, flat base, fits the −y wall below the tray rim | D-01, D-07; `controller mounts below tray rim` |

Precharge (100 Ω + timer) and the contactor coil (key → E-stop → BMS enable)
are already outside the controller in the single-line in
[powerbox.md](powerbox.md). A controller without a contactor driver or internal
precharge is therefore acceptable.

## Layout limits in rev A1

These came from sweeping one parameter at a time through `eox calc`.

### Battery envelope

The cover blank (PB-102) is at 0.979 of the 44 in limit, with about 23 mm
left. Pack height counts twice, because it lengthens both cover end walls.

| Pack L × W × H (mm) | Cover flat (mm) | Result |
|---|---|---|
| 500 × 270 × 220 | 1074 × 631 | 0.961 |
| 520 × 270 × 220 (REF) | 1094 × 631 | 0.979 WARN |
| 520 × 330 × 220 | 1094 × 690 | 0.979 WARN |
| 540 × 270 × 220 | 1114 × 631 | 0.996 WARN |
| 545 × 270 × 220 | 1119 × 631 | **FAIL** |
| 520 × 270 × 232 | 1118 × 655 | 1.00 WARN (at the limit) |

Rule of thumb: a top-terminal pack fits while
**(L − 520) + 2 × (H − 220) ≤ 23 mm**. Width is nearly free, with about
130 mm of slack on the 30 in side. A wider pack just makes a wider box. A
side-terminal pack can cut `terminal_clearance` (35 mm) and win back height.

### Motor face

The motor bolts to the +y wall of the tray, which is 150 mm tall.

- **Ø182 motors** (Golden Motor HPM3000B, Motenergy ME171x) do not fit. Their
  150 or 114 mm spigot and 149–170 mm bolt circle run past the rim, and the
  doubler and wall edge-distance checks go negative.
- Raising `tray_height` to 190 mm still leaves the doubler short, and the
  tray blank becomes 1181 mm, past the 44 in limit (1117.6 mm).
- A **130 mm square-flange motor** fits. Only the 0.250 in doubler's edge
  distance is short: 4.96 mm against 12.7 mm, because the bolts sit at the
  flange corners. `tray_height = 160` with `floor_clearance = 15` clears it.

### Controller footprint

The controller lies flat on the −y wall, with M6 rivnuts below the tray rim.
It fits when its footprint is **≤ 170 mm along x** (otherwise the motor bay
grows and the cover blank goes over the limit) and **≤ ~122 mm tall**. The
height limit comes from 15 mm off the floor and a 140 mm rim limit.

| Controller | Footprint (mm) | Result in rev A1 |
|---|---|---|
| Kelly KLS7215ND | 125 × 85 | fits |
| Curtis F2-A | 155 × 120 | fits |
| Fardriver ND72360 | 189 × 121 | fits (cover 0.996) |
| Kelly KLS7230ND | 196 × 110 | cover blank 1120 mm, 2.4 mm **over** |
| Sevcon Gen4 Size 2 | 187 × 165 | top at 183 mm, **above the rim** |
| EZkontrol A48400 | 200 × 164 | **above the rim and over the blank** |

`powerbox.py` places the controller's M6 rivnuts 12 mm in from each corner.
The real hole patterns differ, as each candidate below lists. That pattern is
not a TOML key yet.

## Motor efficiency at mowing pace

At mowing pace (5 km/h, 40:1) the motor turns about 2,320 rpm at about
2.2 N·m, roughly a third of rated torque. That load point is where the
`efficiency` key is used. Datasheet peak figures sit much higher on the load
curve. Two vendors publish measured data at 48 V (DC input to shaft, measured
on their test controllers):

| Torque | Golden Motor HPM3000B ([dyno table](https://www.goldenmotor.com/hubmotors/hubmotor-imgs/HPM3000-48V3KW%20Data.pdf)) | Motenergy ME1717 ([plot](https://sep.turbifycdn.com/ty/cdn/yhst-129399866319704/ME1716ME1717Plots.pdf), read from the curve) |
|---|---|---|
| ~1 N·m | 61 % (715 W input at 0.7 N·m, no load) | ~0.72 |
| ~2 N·m | 77.5 % (2.1 N·m) | ~0.80 |
| ~3 N·m | 84.2 % | ~0.83 |
| ~6.5 N·m | 90.8 % | ~0.89 |

Rev A1 moved the motor into its own vented bay, so efficiency no longer
decides the pack temperature. Changing only `[motor] efficiency`:

| Motor efficiency | Motor-bay heat | Pack, fan on / fan failed | Motor-bay air, fan on (limit 55 °C) |
|---|---|---|---|
| 0.75 | 214 W | 45.7 / 48.5 °C | 47.5 °C |
| 0.80 | 168 W | 44.9 / 47.3 °C | 45.0 °C |
| 0.85 (REF) | 128 W | 44.1 / 46.2 °C | 42.8 °C |
| 0.90 | 92 W | 43.5 / 45.2 °C | 40.9 °C |

**Use ~0.80 for any of these motors**, not the peak figure. All the checks
pass down to 0.75.

---

## Battery candidates

| | Himax LAF48100 | U.S. Battery US 48V105 | LiTime GC Smart 48V 100Ah |
|---|---|---|---|
| Price | $799 | $2,690 | $1,000 |
| L × W × H (mm) | 520 × 269 × 220 | 443 × 320 × 262 | 520 × 268 × 220 |
| Fits rev A1 | Yes | Only with side-terminal clearance (see below) | Yes |
| Continuous / peak | 150 A / UNKNOWN | 150 A / 250 A 30 s | 100 A / 600 A 1 s |
| Cell OVP | 3.65 V listed; **3.682 V max measured** with 66 V applied | **3.65 V** (manual) | UNKNOWN |
| Charge temperature cutoffs | 0–50 °C; BMS stopped at 51.8 °C in test | < 0 °C; **> 65 °C** | < 0 °C; high trip UNKNOWN |
| Listing | IEC 62619 **test report** read; CB certificate not found; propagation **N/A** | UL 2271 **claimed** by the maker; no file number | **None** (FCC/CE/UN38.3) |

### B1 · Himax LAF48100 (CHINS LAF48100) — recommended

- Maker: <https://www.himaxelectronics.com/51-2v-100ah-lifepo4-battery-golf-cart-marine/>
- IEC 62619:2022 test report TSZ25HK022A02-01, issued 2026-06-26 by
  Shenzhen Tiansu Calibration and Testing:
  <https://www.himaxelectronics.com/wp-content/uploads/2026/07/51.2V100AH-TEST-REPORT-IEC-62619.pdf>
- Retail as CHINS LAF48100, **$798.99** with an 18 A charger:
  <https://www.shopabunda.com/products/chins-48v-100ah-lithium-golf-cart-battery-bluetooth-lifepo4-battery-built-in-200a-bms-peak-current-1000a-includes-48v-18a-lithium-battery-charger-and-monitor-perfect-for-golf-carts-rv-etc>
  (also on Amazon, ASIN [B0D9Q8V6V8](https://www.amazon.com/dp/B0D9Q8V6V8))

The report PDF was downloaded and read for this file. What it shows:

- 16S1P of Cornex PF160-100A cells. The cells have their own IEC 62619
  certificate, TÜV JPTUV-147063.
- Pack ratings: 51.2 V, 100 Ah, maximum discharge 150 A, charging 0–50 °C,
  discharging −20–55 °C.
- **8.2.2 overcharge-voltage test:** 66 V applied to the whole pack. Maximum
  cell 3.682 V, pack 58.641 V; "did not exceed the upper limit charging
  voltage". This shows S-01 holds under a charger fault.
- **8.2.4 overheating test:** charging stopped at 51.8 °C cell-case.
- Drop-test sample mass 37.506 kg.

What fails or can't be verified:

- **Not a certificate.** The report says it is not valid as a CB report unless
  appended to an NCB-issued CB Test Certificate. No certificate number was
  found.
- **Pack propagation is not tested.** Clause 7.3 (internal short / 7.3.3
  propagation) is marked N/A and leans on the cell approval. S-02 asks for
  propagation on packs over 1 kWh. Ask Himax for 7.3.3 evidence or a
  UL 2271 §45 result.
- **Brand chain unverified.** The tested unit is labelled "HiMASSi", and
  CHINS's listings name Shenzhen Grenergy as the manufacturer. Buy direct
  from Himax, or get written confirmation that CHINS stock is the tested
  design.
- **No real peak rating.** The retail "1000 A peak" is not credible next to
  150 A in the report. Internal resistance is UNKNOWN. There is no CAN, only
  Bluetooth.
- **Height may not be 220 mm.** The retail height is 8.66 in, but the report
  lists a 200 mm lower cover plus a 31 mm lid with the overlap unknown.
  Measure it: anything over 231 mm breaks the cover blank.

```toml
[battery]  # Himax LAF48100 — IEC 62619 report TSZ25HK022A02-01 unless noted
capacity_ah = 100
cell_min_v = 2.50                 # report: declared discharge cut-off 40 V (CHINS listing: LVD 46.4 V = 2.90 V/cell)
internal_resistance_mohm = 20     # UNKNOWN - keep REF
max_continuous_a = 150            # report "maximum discharge current"
max_peak_a = 150                  # no verified peak rating; 150 A is the only rated figure (retail "1000 A" not credible)
max_temp_discharge_c = 55         # report -20..55 C (retail says 60)
max_temp_charge_c = 50            # report 0..50 C; BMS stopped charge at 51.8 C (8.2.4)
bms_cell_ovp_v = 3.65             # listing pack OVP 58.4 V; 8.2.2 test max cell 3.682 V at 66 V applied
mass_kg = 37.5                    # report drop-test sample 37.506 kg
length = 520                      # 20.47 in (listing); lower cover 518 mm (report)
width = 269                       # 10.59 in (listing); covers 268 mm (report)
height = 220                      # 8.66 in (listing) - MEASURE: report 200 mm lower cover + 31 mm lid
```

### B2 · U.S. Battery US 48V105 — best BMS documentation, UL 2271 claimed

- Product page: <https://www.usbattery.com/us-48v-105/>
- Datasheet: <https://www.usbattery.com/us_48v_105_926/>
- Manual (2024): <https://www.solar-electric.com/lib/wind-sun/Essential_Li_24V_48V_user-manual.pdf>
- Price **$2,690.14** at <https://www.solar-electric.com/us-battery-essential-li-us-48v-105.html>
  (freight; the page notes a minimum order of 8)

Strengths:

- BMS fully tabulated: cell OVP 3.65 V (release 3.40 V), cell UVP 2.50 V.
- Over-current tiers from 160 A / 120 s up to 500 A / 30 ms. Datasheet ratings
  150 A continuous, 250 A for 30 s.
- CAN, IP67 steel case, 42 kg.

Fails / unknowns:

- **Listing unverified.** The datasheet and a 2025-07-18
  [press release](https://www.usbattery.com/us48v105-added-to-the-essential-li-line-of-batteries-that-are-ul-2271-certified/)
  say UL 2271, though the release body even reads "UL 2771". Neither gives a
  UL file number. The 2024 manual lists only cell-level UL 2580 for this
  model. UL Product iQ needs a login, so ask U.S. Battery for the E-number.
- **Hot charging is not blocked** until the cells reach 65 °C. The operating
  spec is 0–55 °C, so the charger must enforce the limit (it has CAN).
- **Envelope.** 443 × 320 × 262 mm, with the M8 terminals on the **side**.
  - With the REF 35 mm `terminal_clearance` the cover blank is 764 mm wide:
    FAIL by 2 mm on the 30 in side.
  - With `terminal_clearance = 15` it fits, giving a box of
    732 × 395 × 290 mm. Side cable routing then has to be designed.

```toml
[battery]  # U.S. Battery US 48V105 (datasheet rev 2025-07; manual Table 6)
capacity_ah = 105
cell_min_v = 2.50                 # manual: cell UVP 2.50 V (release 2.90 V)
internal_resistance_mohm = 20     # UNKNOWN - keep REF
max_continuous_a = 150
max_peak_a = 250                  # 30 s (300 A for 10 s)
max_temp_discharge_c = 60         # operating; BMS trip > 65 C
max_temp_charge_c = 55            # operating spec; BMS does NOT block until > 65 C
bms_cell_ovp_v = 3.65             # manual "Charge Over Voltage Protection (Cell)"
mass_kg = 42
length = 443                      # 17.44 in, +/-3 mm
width = 320                       # 12.60 in
height = 262                      # 10.32 in
terminal_clearance = 15           # terminals are on the side face; needs a side cable route instead
```

### B3 · LiTime 48V 100Ah GC Smart — mechanical reference only

- Product page: <https://www.litime.com/products/48v-100ah-lithium-golf-cart-bluetooth-battery>
  — **$999.99**
- [User manual](https://cdn.shopify.com/s/files/1/0667/7220/5788/files/LiTime_51.2V_100Ah_Golf_Cart_Smart_Battery_-_User_Manual_1f5b6016-9bb7-4531-8565-64c89f372d3a.pdf?v=1754648031):
  520 × 268 × 220 mm, top M8 terminals, IP65, ≤ 40 mΩ, 100 A continuous,
  600 A for 1 s, charge cut below 0 °C, 60 °C maximum discharge.

It matches the REF envelope exactly, but **fails certification**: it lists
only FCC/CE/RoHS/UN38.3 and says its cells are "UL certified". The cell OVP
is UNKNOWN, since only the 57.6 V charge setpoint is given. Don't use it
unless LiTime produces an IEC 62619 or UL 2271 certificate and a BMS sheet
showing OVP ≤ 3.70 V.

```toml
[battery]  # LiTime L51.2V100-200-GC-BT (user manual 2025-07)
capacity_ah = 100
cell_min_v = 2.75                 # UNKNOWN - keep REF
internal_resistance_mohm = 40     # "<= 40 mOhm"
max_continuous_a = 100
max_peak_a = 600                  # 1 s only
max_temp_discharge_c = 60
max_temp_charge_c = 50            # charge range 0..50 C; no trip value published
bms_cell_ovp_v = 3.70             # UNKNOWN - keep REF (only a 57.6 V charge setpoint is published)
mass_kg = 37.2                    # 82 lb
length = 520
width = 268
height = 220
```

### Also screened

| Pack | Why not |
|---|---|
| Vatrer 48V 105Ah | Intertek UL 2271 cETLus is claimed in a [press release](https://investor.wedbush.com/wedbush/article/newsfile-2026-9-3-vatrer-introduces-48v-105ah-lithium-golf-cart-battery), but no control number was found. Every variant breaks the envelope; standard is 500 × 318 × 244 mm, cover blank 1122 mm FAIL. OVP UNKNOWN. vatrerpower.com blocked fetching. |
| VEVOR HD-51.2-100-SK | Fits at 520 × 268 × 220 mm and the BMS is app-adjustable, but only FCC was found. |
| RoyPow S51105, Epoch BB51105A, Trojan TR 48-110, Polinovel, Redway, Millertech, Leoch | ≥ 282 mm wide and/or > 220 mm tall, or longer than 540 mm. Most claim only cell-level certification. |
| RELiON InSight, U.S. Battery GC2, Discover GC2 | 30 Ah modules; would need parallel packs. |
| Dakota Lithium 48V 96Ah | Fits, but discontinued. |

---

## Motor candidates

| | BLDC.com DH130BLD2300 | Motenergy ME1717 (ME1716) | Golden Motor HPM3000B |
|---|---|---|---|
| Price | $752 (40–45 day lead) | $650 for the ME1716; ME1717 not priced | $396 |
| Rated | 2300 W, 7.32 N·m, 3000 rpm | 4000 W, 9.55 N·m, 4000 rpm | 3000 W, 4000 rpm |
| Peak / no-load speed | 23 N·m / 3600 rpm | 24 N·m stall / ~5200 rpm | 25 N·m claimed (20.8 tested) / 4489 rpm |
| Ratio for 8 km/h at 44 V | ~36 | ~50 | ~44 |
| Face | 130 square, 4 × Ø9 on PCD 145, Ø110 spigot | NEMA 143TC: 4 × 3/8-16 on 149.2, Ø114.3 | Ø182, 4 × M8 on PCD 170, Ø150 spigot |
| Fits the 150 mm wall | **Yes** (doubler edge-distance fix) | No | No |
| Cooling / IP | IP65, no fan | IP65 TENV, KTY84 sensor | **Fan-cooled**; IP65 or IP54 (sources conflict) |
| Efficiency data | Vendor "85 %"; rated point implies 0.80 | Measured curve | Measured dyno table |

### M1 · BLDC.com BLDC-DH130BLD2300, 48 V — recommended

- Product page: <https://www.bldc.com/2300w-bldc-motor> — **$751.52**, 48 V
  winding, free shipping, 40–45 day delivery.
- Drawing: <https://www.bldc.com/images/uploaded/2300w-bldc-motor-dimension.jpg>,
  read for this file.

Spec table, as given on the page:

- 2300 W, 48 V, 60 A rated current.
- 7.32 N·m at 3000 rpm rated; 23 N·m max torque; 3600 rpm no load.
- "Working efficiency 85 %"; IP65; class F insulation; Halls; 9.05 kg.
- Matched controller: BLDC-KBL/KEB.

Drawing:

- 130 × 130 mm square flange, 4 × Ø9 "EQS" holes on Ø145 at 45°.
- Ø110 −0.05 spigot, 5 mm high.
- 155 ± 1 mm body plus a 34 mm rear cap.
- Ø22 −0.03 × 40 ± 1 mm shaft, 6 mm key, 24.5 mm over-key dimension,
  M6 × 16 centre tap.

Fails / unknowns:

- **Efficiency is only a claim.** 2300 W out / (48 V × 60 A) = 0.80
  (*derived*). There is no curve and no no-load current, so measure it on the
  prototype.
- **Runs at the edge of its continuous rating.** At 36:1 the 15° grade needs
  6.88 N·m against 7.32 N·m rated, which is a WARN. Top speed sags to about
  7.9 km/h on an empty pack (3600 rpm × 44/48).
- **No motor temperature sensor is listed.**
- **Shaft is at the sprocket's limit.** Ø22 mm with a 6 mm key is at the 7/8 in
  maximum bore of a stock 40B11 sprocket, per the
  [Motion listing](https://www.motion.com/products/sku/00163714) seen only as
  a search summary. The chain module should check the hub wall, or use
  12 teeth or more.
- **The 0.250 in doubler needs a layout tweak** (see [Motor face](#motor-face)).

```toml
[motor]  # BLDC.com BLDC-DH130BLD2300, 48 V (product page + dimension drawing)
rated_power_w = 2300
rated_speed_rpm = 3000
peak_torque_nm = 23
max_speed_rpm = 3600              # no-load at 48 V
efficiency = 0.80                 # derived: 2300 W / (48 V x 60 A); vendor says "85 %"; part-load UNKNOWN
diameter = 130                    # SQUARE flange 130 x 130 (bolt holes at the corners)
length = 189                      # 155 body + 34 rear cap, from the flange face
shaft_diameter = 22               # 6 mm key
shaft_length = 40
pilot_diameter = 110
bolt_count = 4
bolt_pcd = 145
bolt_diameter = 8                 # M8 through the Ø9 flange holes
mass_kg = 9.05
```

### M2 · Motenergy ME1717 (Hall) / ME1716 (sin/cos) — best sealed motor, needs a new layout

- ME1717: <https://www.motenergy.com/mepmmo4.html>. No price; the page links
  the ME1718 drawing, so confirm the length.
- ME1716: <https://www.motenergy.com/mepmmo3.html> and
  <https://electricmotorsport.com/me1716-pmac-motor.html> — **$650.00**.
- Drawing: <https://sep.turbifycdn.com/ty/cdn/yhst-129399866319704/ME1716Drawing.pdf>

Specs:

- 4 kW S1 at 48 V, 9.55 N·m at 4000 rpm loaded.
- 100 A continuous, 300 A for 2 min, 24 N·m stall. 6000 rpm mechanical limit.
- IP65, finned and fanless. KTY84-130 in the windings.
- 4.9 mΩ phase-to-phase, 11 kg.
- NEMA 56C/143TC face. 7/8 in shaft with a 3/16 key, which takes an
  off-the-shelf 40BS11-7/8 sprocket.
- The 48 V curve (plotted above) is about 0.80 at 2 N·m and 0.88–0.89 from
  5 to 11 N·m.

Fails in rev A1:

- **It doesn't fit the 150 mm motor wall.** At Ø181.5 the doubler and wall
  edge distances go negative, and it hits the bay fan by 12–15 mm.
- **It is oversized.** Its 4 kW rating makes the `continuous current` check
  read 117–129 A. That check uses rated power, so it also drives the fuse up to
  175 A and fails the 150 A contactor. With a 100 A controller limit the real
  current is lower. Either way the TOML would need `rated_power_w` derated for
  this motor.

```toml
[motor]  # Motenergy ME1716 drawing 0JWT.303.531 (ME1717 = Hall twin, same frame)
rated_power_w = 4000              # drawing title block, S1, 48 V
rated_speed_rpm = 4000            # drawing "loaded speed" (EMS lists 5000)
peak_torque_nm = 24               # EMS "stall torque"
max_speed_rpm = 5200              # ME1717 plot no-load at 48 V (EMS lists 5500 max)
efficiency = 0.78                 # ME1717 plot at ~1.7 N*m (mowing at ~50:1); 0.88 at rated
diameter = 181.5                  # over fins
length = 150                      # mounting face to rear (ME1716; confirm ME1717)
shaft_diameter = 22.23            # 7/8 in, 3/16 in key
shaft_length = 47.6               # from the mounting face
pilot_diameter = 114.3            # 4.5 in
bolt_count = 4
bolt_pcd = 149.2                  # 5.875 in
bolt_diameter = 9.525             # 3/8-16 UNC tapped, 19 deep
mass_kg = 11                      # Motenergy (EMS: 9.3 kg)
```

### M3 · Golden Motor HPM3000B, 48 V — cheapest, but fan-cooled and too big

- Product page: <https://goldenmotor.bike/products/3kw-bldc-motor-air-cooled>
  — **$395.99**
- Drawing: <https://www.goldenmotor.com/hubmotors/hubmotor-imgs/HPM3000B%20Drawing.pdf>
  (2014; the newer key-shaft drawing link on the product page returns 404)
- Dyno table: <https://www.goldenmotor.com/hubmotors/hubmotor-imgs/HPM3000-48V3KW%20Data.pdf>
  (read for this file)

Specs:

- Rated 48 V / 85 A / 3000 W / 4000 rpm, from the dyno header.
- 25 N·m claimed; 20.8 N·m measured at 92.8 A. 4489 rpm near no load.
- Ø20 shaft with a 5 mm key, 33.8 mm beyond the boss.
- 4 × M8 tapped on PCD 170, Ø150 spigot. Halls plus a temperature wire.
- 7.3 kg.

Fails:

- **Too big for the wall.** The Ø182 body and Ø150 spigot have the same
  problem as M2.
- **Fan-cooled.** It has a shaft impeller under a perforated rear cover, and
  the IP rating is IP65 on the shop page but IP54 on the wiring sheet.
- **High no-load loss.** It draws 715 W at near zero load at 4489 rpm, so it
  is only about 77 % efficient at mowing torque.

```toml
[motor]  # Golden Motor HPM3000B 48 V (2014 drawing + dyno table)
rated_power_w = 3000
rated_speed_rpm = 4000
peak_torque_nm = 20.8             # measured max (current-limited test); vendor claims 25
max_speed_rpm = 4489              # 0.7 N*m test point, 48.0 V
efficiency = 0.78                 # dyno: 77.5 % at 2.1 N*m (mowing torque); 90.8 % at 6.5 N*m
diameter = 182
length = 107                      # front boss face to rear fan cover (~101 from the M8 face)
shaft_diameter = 20               # 5 mm key
shaft_length = 33.8               # beyond the Ø114 boss
pilot_diameter = 150
bolt_count = 4
bolt_pcd = 170
bolt_diameter = 8                 # M8 tapped, 15 deep
mass_kg = 7.3                     # product page (wiring sheet: 8)
```

### Also checked

| Motor | Why not |
|---|---|
| Peaco D110BLD2000-30S, [$520.69](https://peacosupport.com/motors/brushless-dc-motors/2kw-brushless-dc-motor) | 110 square, fits the wall. But 3300 rpm no-load forces a ratio of ~33, where the grade needs 7.5 N·m against 6.37 rated: FAIL. IP54, efficiency unpublished. |
| Motenergy ME1117 | Open frame with a built-in fan. |
| QS Motor 120/138 mid-drives | Splined or tapered shafts; mostly 60–72 V. |
| ATO 2 kW 48 V servo | 85 %, encoder only, 2800 rpm. |
| Kunray / "MY1020"-type 48 V 2 kW | No datasheet or drawing. |
| Innotec 145-FZS48-040 (2 kW TENV PMSM) | [Quote only](https://pmgenerators.com/brushless-dc-motors/48-volt-motors/pm-synchronous-motor-145-fzs48-040). Worth asking for as a sealed 2 kW option. |

---

## Controller candidates

None of these publish **input capacitance** or a usable **efficiency**. Keep
the REF values (2000 µF, 0.97). Measure capacitance across B+/B− on an
unpowered unit, or ask the vendor, before finalising the precharge.

| | Kelly KLS7215ND | Sevcon Gen4 Size 2 G4827 | EZkontrol A48400 |
|---|---|---|---|
| Price | $139 | $625, plus programming from $100 | $280 |
| Voltage | 36–86 V | 19.3–69.6 V | 75 V max; minimum UNKNOWN |
| Phase current | 200 A 1 min; up to 110 A continuous | 275 A 2 min; 110 A 60 min | 400 A max; 160 A rated |
| Battery limit | Programmable as 20–100 %, base unstated | Programmable; maximum UNKNOWN | 200 A maximum |
| Feedback | Hall only | Hall, encoder, sin/cos | Hall, ABZ encoder |
| Seat input | No; use Foot_SW | **Yes** | UNKNOWN |
| Contactor driver / precharge | No / no | Yes / yes | Yes / probably |
| IP | IP66 | IP66 with the connector mated | IP66 (web page only) |
| Size (mm) | 125 × 85 × 50 | 187 × 165 × 71 | 200 × 164 × 70.5 |
| Fits rev A1 wall | **Yes** | No (above the rim) | No |

### C1 · Kelly KLS7215ND (KLS-N "Jaguar", 72 V class, 200 A, machined flat base) — recommended

- Shop: <https://kellycontroller.com/shop/brushless/>. Store record for this
  SKU: <https://kellycontroller.com/wp-json/wc/store/v1/products/72877> —
  **$139.00, in stock**.
- Manual, KLS-N rev 2.1.2 (July 2025), which covers every case size:
  <https://media.kellycontroller.com/new/Kelly-Jaguar-series-KLS-NUserManuaV2.12-1.pdf>

From the manual:

- Ratings: 48–72 V nominal, **36–86 V** operating. Motor RMS current
  **200 A for 1 min** and "up to 110 A" continuous, depending on the heatsink.
- Control: sinusoidal SVPWM/FOC, three-phase **Hall only**.
- Inputs: KTY84/KTY83 motor-temperature input; key (PWR); brake switch and
  analog regen; FWD/REV; 0–5 V or Hall throttle.
- Protection: user-set over- and under-voltage limits. Thermal cutback at a
  90 °C case and shutdown at 100 °C.
- **IP66.** Programmed by PC (USB cable, $19) or Android over Bluetooth ($19).
  CAN costs 10 % extra.
- Figure 1 case: **125 × 85 mm, 50 mm high** including an 8 mm base. Holes
  **4 × Ø5.2 on 115 × 75 mm**; M5 power bolts.

Fails / unknowns:

- **Battery current limit isn't in amps.** It is set as a 20–100 %
  percentage and the manual doesn't say of what. Confirm with Kelly that
  100 A is reachable, and whether 200 A phase gives enough of the motor's
  23 N·m peak. The grade-start check passes 3.3× on the motor's own peak,
  which leaves margin.
- **No seat input.** Wire the seat switch in series with Foot_SW, the throttle
  enable on pin 15. Re-check that against S-07 when the controls module is
  designed.
- **No contactor driver and no precharge.** EOX already has both externally.
  The manual's 1 kΩ / 10 W precharge is replaced by the 100 Ω / 50 W timed
  one.
- **Rivnuts must change.** The case needs **M5** rivnuts on 115 × 75 mm, not
  M6 at the code's 12 mm inset (BOM M05/M10).
- **Mass and capacitance UNKNOWN.** The store's 2 lb looks like a shipping
  weight.
- If more current is wanted, the **KLS7230ND** ($179; 280 A for 1 min, up to
  150 A continuous; 196 × 110 × 66 mm; 4 × Ø7 on 180 × 96 mm) is the same
  family. It overshoots the cover blank by 2.4 mm in rev A1.

```toml
[controller]  # Kelly KLS7215ND (KLS-N manual v2.1.2, Figure 1)
battery_current_limit_a = 100     # to program; Kelly sets battery current as 20-100 % (base unstated) - confirm 100 A
# efficiency =                    # UNKNOWN - keep REF ("up to 99 %" is marketing)
# input_capacitance_uf =          # UNKNOWN - keep REF; measure before sizing precharge
length = 125                      # along x; holes 4 x Ø5.2 on 115 x 75 (M5)
width = 85                        # along z
thickness = 50                    # incl. 8 mm base plate
# mass_kg =                       # UNKNOWN - keep REF (store lists 2 lb shipping weight)
```

### C2 · Sevcon Gen4 Size 2, G4827 (36–48 V, 275 A) — most complete, needs a new mounting spot

- <https://www.thunderstruck-ev.com/sevcon-g4827.html> — **$625.00**, in stock.
  It ships unprogrammed; programming from $100, harness from $150.
- [Datasheet G48EN1109B](https://www.thunderstruck-ev.com/Manuals/G48%20Datasheet%20G481109B.pdf)
  and [Gen4 manual rev 3.4](https://www.thunderstruck-ev.com/images/Gen4%20Product%20Manual%20V3%204.pdf)

From the datasheet and manual:

- Range and control: 19.3–69.6 V working, with a programmable over-voltage
  cutback. FOC. Hall (UVW), AB encoder or sin/cos. KTY/NTC input.
- Current: 275 A rms for 2 min, 110 A for 60 min. No current derating up to
  80 °C, though above 25 °C it holds the rating for less time.
- I/O: KSI, a **seat switch** (digital input 4), FWD/REV, footbrake pot,
  0–5/10 V throttle. Three 2 A contactor drivers. **Integrated precharge.**
  CANopen.
- IP66 with the 35-way connector mated (IP42 unmated).
- 187 × 165 × 71 mm, 1.3 kg. 4 × Ø7 on 158 × 173 mm.

It is the only candidate that passes every functional requirement. But at
165 mm tall it doesn't fit below a 150 mm tray rim, rotated or not. Setup
needs Sevcon DVT plus a CANopen dongle, or dealer programming.

```toml
[controller]  # Sevcon Gen4 Size 2 G4827 (manual rev 3.4 p4-6, p4-7)
battery_current_limit_a = 100     # programmable (object 4623h); max battery current UNKNOWN
# efficiency =                    # UNKNOWN - keep REF
# input_capacitance_uf =          # UNKNOWN - keep REF
length = 187
width = 165                       # 4 x Ø7 on 158 x 173
thickness = 71                    # to the top of the signal connector (body 69)
mass_kg = 1.3
```

### C3 · EZkontrol A48400 (Golden Motor) — pairs with the HPM motors

- <https://goldenmotor.bike/product/ezkontrol-48-volt-universal-bldc-controller>
  — **$280.00**, in stock.
- [User manual](https://www.goldenmotor.com/controllers/EZkontrol%20Users%20Manual.pdf)

From the manual:

- 48 V rated, 75 V max. FOC. Hall or ABZ encoder. Motor-temperature input.
- **200 A maximum bus current**; 400 A max / 160 A rated phase current.
- KSI, FWD/REV, high/low brake, throttle, contactor coil output. CAN plus
  RS485, Bluetooth app.
- 200 × 164 × 70.5 mm, 4 × Ø7 on 150.5 × 180 mm.

Unknowns:

- The IP66 rating appears on the web page only.
- Not stated: minimum voltage, mass, regen, or the durations behind the
  ratings.
- No seat input is documented. The Hold and Parking pins aren't explained.
- The 70 °C over-temperature trip is low for a sealed bay.

It doesn't fit rev A1: it is above the rim and over the blank.

```toml
[controller]  # EZkontrol A48400 (user manual p4, p10)
battery_current_limit_a = 100     # to program; manual max bus current 200 A
# efficiency =                    # UNKNOWN - keep REF
# input_capacitance_uf =          # UNKNOWN - keep REF
length = 200
width = 164                       # 4 x Ø7 on 150.5 x 180
thickness = 70.47
# mass_kg =                       # UNKNOWN - keep REF
```

### Also checked

| Controller | Why not |
|---|---|
| Curtis AC F2-A 48-240 ([datasheet](https://cdn.curtisinstruments.com/products/datasheets/ACF2A_datasheet_en.pdf)), €540–$688 | Fits at 155 × 120 × 55 mm and is IP65, with an interlock input and a contactor driver. But its datasheet lists only encoder and sin/cos feedback, **no Hall**. The 50 °C maximum ambient is below the 55 °C REF, and the 63 V maximum is tight. |
| Curtis AC F2-AE ([datasheet](https://cdn.curtisinstruments.com/products/datasheets/ACF2AE_datasheet_en.pdf)) | Lists Hall sensors and IP67, but no retailer was found for a 48 V unit. Ambient is also 50 °C. Worth a distributor quote. |
| Fardriver ND72360 ([maker](http://www.fardriver.com/en/index.php?c=Show&a=index&cid=15&id=14)) | Fits at 189 × 121 mm and is IP67, 170 A DC. But there is no public manual; the continuous rating, contactor driver and seat function are UNKNOWN. Price is unverified (~$150–275 on eBay). |
| Kelly KLS-S, Curtis 1226BL / 1232E / 1232SE, Votol EM, ASI BAC, Golden Motor VEC | Too low a voltage maximum or minimum for 40–59 V, discontinued, IP54, induction or sin/cos only, or no datasheet. |

---

## Recommended set

**Himax LAF48100 + BLDC.com DH130BLD2300 + Kelly KLS7215ND.** About $1,690
for the three, before shipping, a charger and the controller's programming
cable.

This is the only combination of currently purchasable parts found that fits
rev A1 as drawn: 520 mm pack, 150 mm tray wall, controller on the −y wall
below the rim. Each part also has a published, dimensioned document.

### Exact TOML changes

Keys not listed stay as they are.

```toml
[vehicle]
reduction_ratio = 36              # DH130 no-load 3600 rpm; 8 km/h = 3343 rpm (drivetrain module to confirm)

[battery]
cell_min_v = 2.50
max_continuous_a = 150
max_peak_a = 150
max_temp_discharge_c = 55
max_temp_charge_c = 50
bms_cell_ovp_v = 3.65
mass_kg = 37.5
width = 269
# capacity_ah = 100, length = 520, height = 220: unchanged (height to be measured)
# internal_resistance_mohm: unchanged (UNKNOWN)

[motor]
rated_power_w = 2300
peak_torque_nm = 23
max_speed_rpm = 3600
efficiency = 0.80
diameter = 130                    # square flange
length = 189
shaft_diameter = 22
shaft_length = 40
pilot_diameter = 110
bolt_pcd = 145
mass_kg = 9.05
# rated_speed_rpm = 3000, bolt_count = 4, bolt_diameter = 8: unchanged

[controller]
length = 125
width = 85
thickness = 50
# battery_current_limit_a = 100, efficiency, input_capacitance_uf, mass_kg: unchanged (UNKNOWN or already 100)
```

Layout keys are the layout owner's call. They aren't component values, but
the motor makes this change necessary:

```toml
[enclosure]
tray_height = 160                 # with floor_clearance = 15, clears the PB-103 doubler edge-distance FAIL
floor_clearance = 15              # PB-101 flat then 1109 mm (0.993 of 44 in, WARN)
```

### What `eox calc` says with these values

Run against rev A1 on a scratch copy of the TOML.

| Check | Rev A1 REF | Trio | Trio + layout keys |
|---|---|---|---|
| Totals | 0 FAIL, 5 WARN | **1 FAIL**, 3 WARN | **0 FAIL**, 2 WARN |
| Box outer (mm) | 809 × 346 × 268 | 809 × 370 × 268 | 809 × 370 × 268 |
| PB-101 / PB-102 flats | 0.975 / 0.979 WARN | 0.975 / 0.979 WARN | 0.993 WARN / 0.961 |
| PB-103 doubler hole edge | 16.7 mm pass | **4.96 mm < 12.7 FAIL** | pass |
| Pack voltage at BMS trip | 59.2 V WARN | 58.4 V pass | 58.4 V pass |
| Continuous current at empty pack | 55 A | 74 A (≤ 150) | 74 A |
| Climb torque, 15° continuous | 6.20 / 6.37 N·m WARN | 6.88 / 7.32 N·m WARN | same |
| Pack temperature: fan on / failed / charging | 44.1 / 46.2 / 42.9 °C | 44.8 / 47.2 / 42.9 °C (limits 55 / 55 / 50) | same |
| Motor-bay air, fan on | 42.8 °C | 45.0 °C (≤ 55) | same |
| Runtime, drive only | 5.7 h | 5.4 h | 5.4 h |

The charging-in-sun WARN goes away because the Himax charge rating is 50 °C.
The pack's lower 55 °C discharge rating (REF 60 °C) still leaves about 8 °C
of margin with the fan failed.

### Before ordering

1. **Battery.**
   - Get Himax's IECEE CB Test Certificate number and NCB for report
     TSZ25HK022A02-01, and check it on the IECEE site.
   - Get evidence for clause 7.3.3 propagation (S-02).
   - Get a peak-current rating with its duration.
   - Get written confirmation that the CHINS-branded unit is that design, or
     buy from Himax.
   - Measure the assembled height: it must be ≤ 231 mm.
2. **Fallback battery.** If none of that comes through, use the U.S. Battery
   US 48V105, but only once its UL 2271 file number checks out in Product iQ.
   It needs `terminal_clearance = 15` with side cable routing, and the charger
   must stop hot charging.
3. **Motor.**
   - Ask BLDC.com for an efficiency curve or the no-load current, and whether
     a motor temperature sensor is fitted.
   - Confirm the 40–45 day lead time.
   - Tell the drivetrain module about the 36:1 ratio and the Ø22 shaft with a
     6 mm key.
4. **Controller.**
   - Ask Kelly what the "Battery_Current" percentage is a percentage of, and
     for the DC-link capacitance.
   - Update the rivnut pattern to M5 on 115 × 75 mm.
5. **Then** edit `design/powerbox.toml`, re-run `uv run eox calc`, and
   update BOM rows E01–E03.

### If the layout is reworked

If the motor and controller ever get taller walls, for example through a
different tray split, the best-documented set is **Himax LAF48100 + Motenergy
ME1717 + Sevcon Gen4 G4827**:

- A sealed TENV motor with a KTY sensor and a NEMA face.
- A controller with a real seat input, integrated precharge and 80 °C
  capability.

In rev A1 that set gives 5 FAIL: motor/fan clearance, two wall/doubler edge
distances, the controller above the rim, and the contactor rating vs a 175 A
fuse. The last one is only because the 4 kW motor rating feeds the current
check.
