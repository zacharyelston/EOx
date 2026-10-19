# Research: golf-cart drivetrain and steering geometry

Collected 2026-10-18 to lay EOX out around real golf-cart parts. Sources are
factory service manuals (read from their page images on ManualsLib), OEM spec
sheets and parts vendors.

- **UNCONFIRMED:** not found in a public source.
- **DERIVED:** worked out from published numbers.
- Values are in inches as published, with millimetres where we use them.

## What changed in the EOX layout because of this

| Finding | Effect on EOX |
|---|---|
| **The motor axis is parallel to the axle**, not fore-aft. The motor slides onto a splined input on the side of the gear case, held by 3 bolts [M1 p79, M3 p239/257]. Gears: input → intermediate → differential, all on parallel shafts [M3 p258]. Pre-1986 Dana units had the motor perpendicular; avoid those [14]. | Drive-axle module redrawn: the motor sits sideways on the gear case (`design/axle.toml`) |
| **The motor sits above the axle centreline** [M3 p251 figure]. The housing rotates when the spring U-bolts come off [M1 p144]. | Motor axis 60 mm above the axle (REF). The subframe must stop the housing rotating; our U-bolted rails do. |
| **The gear case is off-centre**, and the motor runs out over the longer tube. TXT: case about 3.6 in right of centre (DERIVED from 16-3/4 and 23-7/8 in shafts [9]). Club Car about 3.3 in left [10]; Yamaha about 2.4 in left [10b]. | `diff_offset_y = -90` mm |
| **Rear track 38.5 in** (978 mm): TXT, DS, Precedent [M1, M2 p14, 2] | Track was 880 mm. Frames widened to ±310 mm rails, still inside the tyres. |
| **Ground clearance at the diff: 4.5 in** (114 mm) on 18x8.50-8 tyres: TXT, RXV, Precedent [M1, 4, 2] | Was 140 mm. Pro drive-over deck clearance is now −36 mm. |
| **Controller:** Curtis 1236 is 232 × 165 × 85 mm, IP65 [13]. TXT mounts it under the seat [M1 p53]; Precedent on a plate in the battery bucket [M3 p208]. | Controller envelope updated |
| **Only the E-Z-GO TXT has a self-contained beam front axle.** It sits on two leaf springs with shocks, the rack is bolted to the axle, and the unit comes off as one bolted assembly [M1 p59, p63, p64]. Club Car, RXV and Yamaha are independent suspension tied into the frame [M2 p82, 4, 7]. | Home uses a TXT-style front end |
| **Front track 34.0 in** (864 mm) TXT; wheelbase 65.5–66 in (1,664–1,676 mm) [M1, M2, 2] | Home wheelbase 1,600 mm, front track 860 mm. Frame necks in at the nose to clear the steered wheels. |
| **No OEM rear end gives the 2–3× reduction EOX needs.** Ratios run 12.3–17:1. Lowest found: RXV AC 16.99:1 [4], Onward 14.85 [6], Cushman Titan HD 14.76 [11], aftermarket Dana 15:1 set [8]. | Gearing options in the `Drive` checks (issue 2) |

## Numbers

| Item | Value | Source |
|---|---|---|
| Rear axle ratio | TXT DC 12.44; Precedent 12.3; Carryall electric 12.32; Onward 14.85; RXV ELiTE AC 16.99; Titan HD 14.76 | M1 p185, M3 p25, 5, 6, 4, 11 |
| Input spline | E-Z-GO 1991+ electric: 19-spline shaft (21-tooth gear); RXV 19 splines / 18 teeth. Shared by Yamaha G8–G27, Columbia Par Car, Taylor-Dunn R-380, Cushman Titan | 16, 8 |
| Motors | TXT 48 V DC shunt 3.0 hp continuous; Precedent 3.1 hp; Carryall 300 DC 3.3 hp rated / 13 hp peak; RXV ELiTE AC 3.3 kW; Onward AC 3.5 kW; Drive2 AC 5.0 kW (60 min) | M1 p185, M3 p25, 5, 4, 6, 7 |
| Aftermarket 5 kW AC motor | 54 lb; "7.25x8.5x10.5" (units not stated) | 12 |
| Brakes | Rear mechanical drums, cable-operated, self-adjusting (TXT); foot park brake (Precedent/Onward); RXV AC: motor braking plus an automatic electromagnetic park brake. No hydraulic brakes on any golf model checked. | M1 p185, 2, 6, 4 |
| Turning | TXT 19.0 ft outside clearance circle; DS 17'6"; Precedent 17'4"; RXV 19.0–19.2 ft | M1, M2, 2, 4 |
| Steer angle | About 40° at the outer wheel for the Precedent (DERIVED, from 17'4" and 65.5 in) | – |
| UNCONFIRMED | Axle tube diameter, spring-perch spacing, rear-end weight, OEM motor dimensions and weight, motor fore/aft offset, front steer angle, turns lock to lock, front ground clearance | – |

**Next step:** measure a real TXT rear end and front end. Owner-measurement
threads on buggiesgonewild.com were blocked to our research tool.

## Sources

- M1: E-Z-GO TXT 48V Repair & Service Manual (2010) https://www.manualslib.com/manual/753389/E-Z-Go-Txt-48v.html
- M2: Club Car DS 2004 manual https://www.manualslib.com/manual/1009228/Club-Car-Ds-2004.html
- M3: Club Car Precedent 2014 manual https://www.manualslib.com/manual/2420102/Club-Car-Precedent-2014.html
- 2: Precedent brochure https://cdn.carbase.com/assets/nbgolfcarsdaee005206/270/assets/images/brochure/clubcarprecedent.pdf
- 4: E-Z-GO RXV spec sheets https://cdn.acenda.com/swift/v1/cartmart/images/bucket/files/EZGO-RXV-specs.pdf
- 5: Club Car Carryall brochure https://cdn.carbase.com/assets/nbgolfcarsdaee005206/270/assets/images/brochure/carryallcommercial.pdf
- 6: https://www.clubcar.com/en/personal/golf-carts/onward-2-passenger/specifications
- 7: Yamaha Drive2 factsheet https://cdn2.yamaha-motor.eu/prod/product-assets/2017/DRIVE2/Factsheets/2017-DRIVE2-E_cs-CZ.pdf
- 8: https://vintagegolfcartparts.com/Category/ezgo_axles_gears
- 9: https://www.golfcartgarage.com/ezgo-txt-golf-cart-passenger-side-rear-axle-electric-94-5-gas-83-88/
- 10: https://vintagegolfcartparts.com/Category/club_car_axles_axle
- 10b: https://vintagegolfcartparts.com/Category/yamaha_rear_axles_axle
- 11: https://www.fairchildequipment.com/wp-content/uploads/2023/08/Fairchild-Equipment-cushman-titan-hd.pdf
- 12: https://ecobattery.com/products/eb-power-ac-kit-600a-5kw-club-car-precedent-2004-08
- 13: Curtis 1236/1238 datasheet https://www.e-kart.fr/images/stories/technique/curtis/curtis-controlers-1236-1238-doc.pdf
- 14: https://vintagegolfcartparts.com/Category/ezgo_motors_couplers
- 16: https://www.buggiesunlimited.com/golf-cart/1991-up-ezgo-electric-input-shaft-kit/4834
