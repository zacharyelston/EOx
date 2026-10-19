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
| S-01 | Pack voltage ≤ 60 V DC under normal *and single-fault* conditions to stay SELV | UL 2271 §6.23, §14.2; ECE R100 §2.17 | `Bus: max pack voltage`, `pack voltage at BMS over-voltage trip` (cell OVP ≤ 3.75 V) |
| S-02 | Pack listed to UL 2271 (or IEC 62619); packs > 1 kWh pass single-cell-failure propagation | UL 2271 §1, §45 | BOM P01 spec. Verify the certificate when buying. |
| S-03 | Fuse at the source: within 7 in (178 mm) of the battery terminal | 33 CFR 183.455 | Power box assembly note, BOM P03 |
| S-04 | Circuits ≥ 50 V: fuse ≤ 100 % of conductor ampacity (engine-space derate ×0.85 where it applies) | 33 CFR 183.425 / .455 | `Bus: main fuse <= main cable ampacity`, `branch fuse <= branch cable ampacity` |
| S-05 | Fuse ≥ 125 % of continuous current | NEC 240.4 / 210.20(A) (reference practice) | `Bus: main fuse ...`, `branch fuse ...` |
| S-06 | Fuse DC voltage rating ≥ max pack voltage; interrupt rating ≥ pack short-circuit current | General practice | `Bus: ... DC voltage rating`, `... interrupt rating vs pack short circuit` |
| S-07 | Operator presence control: blades stop if the operator leaves the seat | B71.1 via CPSC Pub. 588 | Seat switch (C03) drops every unit's enable line |
| S-08 | Blades stop within 5 s of disengage or leaving the seat | B71.1 via LSU AgCenter (secondary source) | PTO unit regen braking; deck module to verify |
| S-09 | No mowing in reverse unless overridden; override resets on re-engage, restart, or leaving reverse | B71.1 via CPSC Pub. 588 | Unit enable logic (controls module) |
| S-10 | Pack enclosure at least IP3X / IPX3 | UL 2271 §9.3, §9.4 | Pack spec (P01) |
| S-11 | Live parts finger-proof (IPXXB) even below 60 V, because wet grass is not a dry location | IEC 61140 §5.2.6 (secondary) | Closed box, glands, shrouded connectors (Anderson SB is finger-safe) |

## Design choices (engineering judgement, not quoted from a standard)

| ID | Choice | Why / enforced by |
|---|---|---|
| D-01 | Power box sealed (target IP54); everything outside it IP65+ (unit controllers, connectors, glands IP67/68) | Golf-cart controllers (e.g. Curtis 1236) are sold as IP65; check the sepex controller chosen, or shield it. |
| D-02 | Design loads: 3 g vertical, 2 g longitudinal and lateral, SF 2 on yield | Typical off-road practice for a slow machine. `Box structure: ...` |
| D-03 | Crash: obstacle strike at top speed with 50 mm crush (5 g at 8 km/h); no yield in the battery restraint (SF 1) | ECE R100 road pulses (10–28 g) are for road vehicles; our Δv is much lower. Revisit with test data. |
| D-04 | Maintenance disconnect fitted even though UL 2271 only requires one above 60 V | Safe servicing. BOM P06. |
| D-05 | Timed precharge, and a resistor that survives being left on into a short | `Bus: precharge resistor if left on into a short` |
| D-06 | Pack below its 60 °C discharge / 45 °C charge rating at the end of a full run, starting heat-soaked; WARN within 5 °C | `Box thermal: pack temp ...` |
| D-07 | Units are DC sepex (default) or AC, never series-wound DC, on anything that spins a blade | A series motor over-speeds unloaded: a thrown belt means a runaway blade. Sepex and AC controllers hold a set speed and brake regeneratively. |
| D-08 | One enable chain: key → E-stop → BMS enable → seat switch → every unit; PTO enable also needs the deck-latched signal | `docs/architecture.md`; controls module |
| D-09 | Articulation pinch gap to the footwell ≥ 120 mm at full lock; ≥ 500 mm (or a guard) wherever a body could be; a frame lock bar for transport and service | ISO 13854 (foot 120, body 500 mm, confirmed in docs/research/articulation.md); ISO 10570 frame lock. `Pivot: front half to footwell` |
| D-10 | Steering fast enough to avoid things: lock to lock ≤ 4 s at standstill force | `Steering: lock-to-lock time`. This is why steering is hydraulic, not an electric actuator (~17 s). |
| D-11 | Max working slope = half the lowest static tip angle (each half's stability triangle and the whole machine), ≥ the 15° design slope | Industry practice. `Stability: max working slope` |
| D-12 | The generator wagon connects to the tractor by DC only, so the tractor stays SELV; mains AC (with ground-fault protection) stays on the wagon | `docs/architecture.md` |

## Open items (unverified or not yet designed)

- **Static stability, parking-brake slope and max speed.** No numbers from
  B71.1 or ISO 5395-3 could be confirmed. EOX computes static tip angles
  (see D-11), but the acceptance values must come from B71.1.
  - The only public figure found is MIOSHA Rule 5443(4): no riding up or down
    slopes over 26°, or across slopes over 17°. The Pro's computed working
    slope (18.7°) is above that cross-slope limit, so label the machine for
    17° across.
  - Industry practice is to label half the measured tip angle as the safe
    working slope.
- **Parking brake.** Golf-cart rear ends have cable-operated mechanical drum
  brakes with a foot or automatic park brake. The E-Z-GO RXV AC drivetrain
  instead uses motor braking plus an automatic electromagnetic park brake
  (docs/research/golf-cart.md). The holding slope isn't checked yet.
- **Articulated steering failure.** If hydraulic pressure is lost the machine
  can't steer; the fail-safe (drive inhibit on low pressure) isn't designed
  yet.
- **When ROPS is required** under B71.1. Cal/OSHA §3563 requires ROPS and a
  seat belt on machines designed for ROPS.
- **UL 2753 content.**
- **Retention g-loads for the pack mount.** No public LFP venting numbers were
  found. The pack's own UL 2271 shock test is 25 g / 15 ms for 12–100 kg packs.
  That is a pack test, not a mount design load.
