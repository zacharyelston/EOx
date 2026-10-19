# Safety requirements

This file maps the standards that apply to EOX and the requirements we derive
from them. Each requirement points to the check that enforces it, or is listed
as open. Research was done 2026-10-18 from public sources only. Most standards
are paywalled, so anything marked *not confirmed* must be checked against the
purchased text before anyone calls EOX compliant.

> EOX is a DIY open-hardware project. Following this list does not make a
> machine certified or safe to sell. Builders are responsible for their own
> machine.

## Which standards apply

| Standard | Applies to EOX? | Status |
|---|---|---|
| ANSI/OPEI B71.1-2017, consumer ride-on mowers | Yes, US product standard for ride-on mowers | Paywalled. Some items confirmed via CPSC (below). |
| ISO 5395-1 / -3:2013 (+Amd 1:2017) | **No.** Scope excludes electric and battery mowers. | Use as guidance only. |
| ISO/NP 62841-4-15, battery ride-on mowers (≤250 V DC) | Future equivalent | New-project ballot 24 Mar 2026; no text yet. |
| UL 2753, Outline of Investigation for Battery Operated Ride-On Lawn Mowers | Likely US listing route (UL 82 points there) | Title seen only in a search snippet. Not confirmed. |
| ISO 21299:2009, ROPS for ride-on turf machines ≤3000 kg | Yes, if ROPS is fitted | Doesn't decide *when* ROPS is required. |
| **UL 2271:2023**, LEV batteries | **Yes, the battery pack** | Full text public: <https://law.resource.org/pub/us/cfr/ibr/inc/ul/ul.s2271.3.2023.pdf> |
| IEC 62619:2022, industrial lithium batteries | Acceptable alternative for the pack | Paywalled. |
| UL 1973 (stationary) / IEC 62133-2 (portable) | **No.** Wrong application. | Many 48 V rack packs carry UL 1973; don't buy those. |
| 33 CFR 183.425 / .455 (USCG, same basis as ABYC E-11) | Borrowed for DC conductor and fuse sizing | Public. |
| IEC 60529 IP codes | Enclosure rating | Public definitions. |

## Confirmed requirements and how EOX meets them

| ID | Requirement | Source | Enforced by |
|---|---|---|---|
| S-01 | Pack voltage ≤ 60 V DC under normal *and single-fault* conditions to stay SELV | UL 2271 §6.23, §14.2; ECE R100 §2.17 | `Electrical: max pack voltage`, `pack voltage at BMS over-voltage trip` (cell OVP ≤ 3.75 V) |
| S-02 | Pack listed to UL 2271 (or IEC 62619); packs > 1 kWh pass single-cell-failure propagation | UL 2271 §1, §45 | BOM E01 spec. Verify the certificate when buying. |
| S-03 | Fuse at the source: within 7 in (178 mm) of the battery terminal | 33 CFR 183.455 | Assembly note, BOM E05 |
| S-04 | Circuits ≥ 50 V: fuse ≤ 100 % of conductor ampacity; engine-space derate ×0.85 | 33 CFR 183.425 / .455 | `Electrical: fuse <= conductor ampacity` |
| S-05 | Fuse ≥ 125 % of continuous current | NEC 240.4 / 210.20(A) (reference practice) | `Electrical: main fuse ...` |
| S-06 | Fuse DC voltage rating ≥ max pack voltage; interrupt rating ≥ pack short-circuit current | General practice | `Electrical: fuse DC voltage`, `fuse interrupt rating` |
| S-07 | Operator presence control: blades stop if the operator leaves the seat | B71.1 via CPSC Pub. 588 | Controller input (BOM E03, E13). Implemented in the controls module. |
| S-08 | Blades stop within 5 s of disengage or leaving the seat | B71.1 via LSU AgCenter (secondary source) | Mower deck module |
| S-09 | No mowing in reverse unless overridden; override resets on re-engage, restart, or leaving reverse | B71.1 via CPSC Pub. 588 | Controls module |
| S-10 | Pack enclosure at least IP3X / IPX3 | UL 2271 §9.3, §9.4 | Pack spec (E01) |
| S-11 | Live parts finger-proof (IPXXB) even below 60 V, because wet grass is not a dry location | IEC 61140 §5.2.6 (secondary) | Closed box, glands, shrouded terminals |

## Design choices (engineering judgement, not quoted from a standard)

| ID | Choice | Why |
|---|---|---|
| D-01 | Box target IP54; electrics inside at least IP65 (controller, DC-DC, glands IP67/68) | The Curtis 1236 traction controller is sold as IP65. This is EOX's own target. |
| D-02 | Design loads: 3 g vertical, 2 g longitudinal and lateral, SF 2 on yield | Typical off-road practice for a slow machine. |
| D-03 | Crash: obstacle strike at top speed with 50 mm crush (5 g at 8 km/h); no yield in the battery restraint (SF 1) | ECE R100 road pulses (10–28 g) are for road vehicles. Our Δv is much lower. Revisit with test data. |
| D-04 | Maintenance disconnect fitted even though UL 2271 only requires one above 60 V | Safe servicing. |
| D-05 | Timed precharge, and a resistor that survives being left on into a short | `Electrical: precharge resistor if left on into a short` |
| D-06 | Pack stays below its 60 °C discharge / 45 °C charge rating, including with the bay fan failed; WARN within 5 °C | `Thermal: pack temp ...`. Rev A1 passes; parked charging in sun is a WARN. |
| D-07 | Sealed battery bay; the ventilated motor bay is a wet zone where every component is IP65+ and the floor slots drain it | Bulkhead PB-106, BOM specs E04, E05, E10, E17, E18 |

## Open items (unverified or not yet designed)

- **Static stability, parking-brake slope and max speed.** No numbers from
  B71.1 or ISO 5395-3 could be confirmed. These are tractor-level checks; buy
  B71.1 before the chassis module.
  - The only public figure found is MIOSHA Rule 5443(4): no riding up or down
    slopes over 26°, or across slopes over 17°.
  - Industry practice is to label half the measured tip angle as the safe
    working slope.
- **When ROPS is required** under B71.1. Cal/OSHA §3563 requires ROPS and a
  seat belt on machines designed for ROPS.
- **UL 2753 content.**
- **Retention g-loads for the pack mount.** No public LFP venting numbers were
  found. The pack's own UL 2271 shock test is 25 g / 15 ms for 12–100 kg packs.
  That is a pack test, not a mount design load.
