# EOX architecture

![EOX Pro layout, P0](img/pro-layout.png)

EOX splits a garden tractor's work into standard **3 HP units** on one
**48 V bus**. Each unit is a golf-cart motor plus its controller. Driving,
mowing and hydraulics are all the same unit; a big job bundles several.
Most of the hardware comes from the golf-cart parts ecosystem: rear ends,
motors, controllers, 48 V LiFePO4 packs, chargers, contactors and 18x8.50-8
wheels.

Numbers on this page are from `uv run eox calc --model pro` at model rev P0 /
power box rev B0. Re-run it for current values.

## Two product lines, shared parts

| | **EOX Pro** | **EOX Home** (planned) |
|---|---|---|
| Layout | Articulated: two halves on a centre pivot | Conventional: steering front axle, driven rear |
| Drive | AWD: 2 drive-axle modules | 2WD: 1 drive-axle module + golf-cart front steering axle |
| Steering | Hydraulic cylinder at the pivot | Mechanical, at the front wheels |
| Units at once | 3 (2 drive + PTO, or 3 hydraulic) | 2 (drive + PTO) |
| Shared | Battery & distribution box, drive-axle module, 3 HP unit, attachments, bus connector | same |

The design files mirror this: `design/units.toml`, `axle.toml` and
`powerbox.toml` are shared; `design/models/pro.toml` (and later `home.toml`)
holds what differs. `eox calc --model <name>` runs every check for one model.

## The 3 HP unit

| | |
|---|---|
| Motor | 48 V **AC induction** golf-cart motor, ~2.2 kW continuous (REF), ~3× peak torque |
| Controller | 48 V AC controller (Curtis 1236/1238 class): programmable battery-current limit (100 A), speed limit, regen, CAN |
| Interface | Anderson SB120 for power, Deutsch DT 6-pin for enable, interlock and CAN |
| Draw at rated power | 62 A at an empty pack (44 V) |

**Why AC and not the cheaper series-DC golf-cart motors.** A series-wound
motor speeds up without limit when it loses its load. On a blade drive, a
thrown belt could turn into a runaway blade; a 21 in blade's tip-speed limit is
about 3,450 rpm. AC units hold their set speed, brake regeneratively (which
helps meet the 5 s blade stop), and give the drive hill-hold.

## The 48 V bus

The **battery & distribution box** is the hub ([docs/powerbox.md](powerbox.md)).
It holds:

- the pack and its main protection (contactor, precharge, maintenance
  disconnect);
- one fused branch per unit;
- the DC-DC converter for 12 V.

The bus stays at or below **60 V DC**, under single fault too, so it is SELV
(see [safety requirements](safety-requirements.md)).

| | P0 value |
|---|---|
| Sized for | 3 units at rated power at once = 185 A (pack: 200 A continuous / 400 A peak) |
| Main fuse / cable | 300 A Class T / 2/0 AWG |
| Branch fuse / cable | 100 A per unit / 6 AWG, 0.9 % drop over 5 m |
| Precharge | 47 Ω, 1.1 s with 4 controllers on the bus |

### Operating modes

These are averages over a job, on one 51.2 V 100 Ah pack (4.1 kWh usable).

| Mode | Units | Battery power | Runtime | Target |
|---|---|---|---|---|
| Mowing (5 km/h, flat) | 2 drive + PTO | 2.9 kW | 1.4 h | 1.5 h: WARN |
| Mowing a 10° slope (3 km/h) | 2 drive + PTO | 3.5 kW | 1.2 h | 1.0 h |
| Transport (8 km/h) | 2 drive | 1.6 kW | 2.6 h | 3.0 h: WARN |
| Backhoe | 3 hydraulic | 5.1 kW | 0.8 h | 1.0 h: WARN |

A Pro doing real work wants more than one 100 Ah pack. The options (tracked in
the issues) are:

- a larger or second pack;
- the generator wagon;
- swappable packs.

## EOX Pro: articulated AWD

```
        rear half                      pivot                     front half
  seat + operator                        ●                 battery & distribution box
  ─────[rear axle module]═══motor══> ─── ● ─── <══motor═══[front axle module]──── implement face
        (golf-cart rear end)        yaw + roll free,        (golf-cart rear end)
                                    pitch locked
```

**Drive-axle module.** A golf-cart rear end with one 3 HP unit. The motor
bolts to the rear end and faces the pivot, the controller sits beside it, and
the module is clamped to a sheet-steel subframe with U-bolts.

**Centre pivot.**

- A vertical pin for steering, up to ±35°.
- A fore-aft pin that lets the halves roll ±10° relative to each other, so all
  four wheels stay on the ground.
- Pitch is locked, so the halves share fore-aft loads.

**Mass.**

- 299 kg without the operator.
- The axle split with the operator is 41 / 59 (front / rear).
- A front implement brings it toward 50 / 50.

**Stability (static).**

| | Tip angle |
|---|---|
| Whole machine | 45° straight, 41° at full lock |
| Front half's triangle (its wheels + pivot) | 52° |
| Rear half's triangle | 37° |
| Half the lowest, used as the max working slope | 18.7° (design slope 15°) |

These are industry practice, not values confirmed from B71.1.

**Steering.**

- Articulating at a standstill needs about 900 N·m, because the tyres scrub
  sideways.
- A 40 mm hydraulic cylinder at 100 bar gives 1,160 N·m and goes lock to lock
  in 2.8 s, from a small 48 V power unit.
- An 8 kN electric actuator gives similar force but takes ~17 s lock to lock,
  which is too slow.
- The outer turning radius is 2.6 m.

**Pinch zone.** At full lock, the front half stays 248 mm from the operator's
footwell. ISO 13854's minimum gap for a foot is 120 mm.

**Gearing (open).** Stock golf-cart rear ends (~12.4:1) are geared for 25 km/h.

| Option | Torque per motor on a sustained 10° climb |
|---|---|
| Stock | 1.8× rated (WARN) |
| ~2:1 stage added | 0.9× rated |
| 3:1 stage added | 0.6× rated, and ~8 km/h at base speed |

## Attachments

**Mower deck.**

- The deck carries its own PTO unit, so the coupling is mechanical plus one
  connector, not a shaft.
- **Front-mount vs drive-over is open.** A golf-cart diff hangs about 140 mm
  above the ground, which is 10 mm *lower* than the top of a typical deck at
  its lowest cut height. The front axle can't roll over the deck as drawn.
- **Magnetic coupling: switchable permanent magnets.** They hold with no power,
  so a power loss can't drop the deck.
- **Steel strike plates on the deck.** Our box shells are aluminium, and magnets
  need steel.
- **Cones or pins take the sideways load.** Magnets only hold about 20–25 % of
  their pull in shear.
- **Interlock:** the PTO cannot start unless the deck reports latched.

**Hydraulic attachments (backhoe, log splitter).** Three units bundled on a
pump drive. A backhoe peak of about 6 gpm at 2000 psi is 6.1 kW at the shaft,
2.7 units.

**Generator wagon.**

- A towed wagon with a generator, ground-fault-protected AC outlets for corded
  tools, and the 48 V charger.
- **The tractor stays SELV:** the wagon connects to it only by a DC plug (the
  charge inlet).
- Exhaust points away from the operator.
- A ~2.2 kVA inverter generator roughly covers average mowing load.

## Open decisions

Each one is a GitHub issue at <https://github.com/zacharyelston/EOx/issues>:

- gearing;
- deck mount;
- pack size and swapping;
- subframe and pivot CAD;
- steering hydraulics;
- the unit connector and CAN standard;
- the Home model;
- the generator wagon;
- stability numbers against B71.1;
- prototype validation.
