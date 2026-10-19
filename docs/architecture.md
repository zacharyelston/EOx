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

| | **EOX Pro** (P0) | **EOX Home** (H0) |
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
| Motor | The golf cart's own 48 V **DC sepex** motor, used or rebuilt: ~3 hp continuous (E-Z-GO TXT 3.0 hp), ~4× peak (Carryall 3.3 hp rated / 13 hp peak) |
| Controller | 48 V sepex controller (Curtis 1268 / Alltrax class): battery-current limit (100 A), speed limit, regen braking, key/enable input |
| Interface | Anderson SB120 for power, Deutsch DT 6-pin for enable, interlock and CAN |
| Draw at rated power | 66 A at an empty pack (44 V) |

**Why sepex DC: simple and serviceable.**

- **Cheap and fixable:** it is the motor most golf carts already have, used or
  rebuilt for a few hundred dollars, and any golf-cart shop can replace its
  brushes.
- **Controllable:** unlike a series-wound motor, a sepex motor's field is
  controlled separately, so the controller holds a set speed and brakes
  regeneratively. That keeps a blade drive under control and helps meet the
  5 s blade stop.
- **Never series-wound DC on a blade:** a series motor speeds up without limit
  when it loses its load, so a thrown belt would mean a runaway blade (a 21 in
  blade's tip-speed limit is about 3,450 rpm).
- **AC is an optional upgrade:** E-Z-GO RXV and Club Car AC motors and
  controllers fit, at several times the cost.

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
| Sized for | 3 units at rated power at once = 197 A (pack: 200 A continuous / 400 A peak) |
| Main fuse / cable | 300 A Class T / 2/0 AWG |
| Branch fuse / cable | 100 A per unit / 6 AWG, 0.9 % drop over 5 m |
| Precharge | 47 Ω, 1.1 s with 4 controllers on the bus |

### Operating modes

These are averages over a job, on one 51.2 V 100 Ah pack (4.1 kWh usable).

| Mode | Units | Battery power | Runtime | Target |
|---|---|---|---|---|
| Mowing (5 km/h, flat) | 2 drive + PTO | 3.2 kW | 1.3 h | 1.5 h: WARN |
| Mowing a 10° slope (3 km/h) | 2 drive + PTO | 3.9 kW | 1.0 h | 1.0 h |
| Transport (8 km/h) | 2 drive | 1.7 kW | 2.4 h | 3.0 h: WARN |
| Backhoe | 3 hydraulic | 5.4 kW | 0.8 h | 1.0 h: WARN |

A Pro doing real work wants more than one 100 Ah pack. The options (tracked in
the issues) are:

- a larger or second pack;
- the generator wagon;
- swappable packs.

## EOX Home: steering front axle, 2WD

![EOX Home, layout H0](img/home-layout.png)

```
   rear                                                                     front
   hitch ─[controller]─[rear axle + sideways motor]   box (seat on top)   floor   [rack + TXT beam axle]
                                                      slung low between rails      frame necks in here
```

The Home is a golf cart turned into a tractor. The geometry follows
[docs/research/golf-cart.md](research/golf-cart.md).

- **Drive-axle module:** the same module as the Pro, at the rear. The motor
  sits sideways on the off-centre gear case.
- **Battery & distribution box:** slung low between the rails just ahead of
  the rear axle, as golf carts carry their batteries. The seat sits on it at
  about 0.6 m.
- **Front:** an E-Z-GO TXT-style beam front axle with its rack bolted on. It is
  the only self-contained golf-cart front axle we found. The frame necks in to
  ±100 mm at the nose so the steered wheels can sweep.
- **Mid-mount deck:** fits under the box, with its PTO unit standing on it
  outboard of the left rail. The front axle has no diff, so it clears the deck
  by +50 mm (REF) and the tractor can drive over it to hitch up.

| | H0 value |
|---|---|
| Machine mass | 237 kg without operator; 302 kg with the deck and its PTO unit |
| Wheelbase / tracks | 1,600 mm / rear 978, front 860 mm |
| Axle split (with operator) | 33 / 67 front / rear; 36 / 64 with the deck |
| Turning radius | 2.8 m, outer front tyre, at a 50° inner lock (REF) |
| Steering effort | ~90 N at the rim to steer at a standstill (estimate) |
| Rated climb, deck fitted | 12° short climbs (rear-tyre grip runs out near 14° on turf) |
| Front axle load climbing 12° | 27 % of weight, enough to keep steering (≥ 15 %) |
| Stability | 45° tip angle (worse of bare and deck-fitted), so a 22.7° max working slope |
| Runtime on one pack | 1.39 h mowing (target 1.5), 3.0 h transport |

**Gearing and rated slope: 15:1, 12° ([issue 2](https://github.com/zacharyelston/EOx/issues/2)).**
Climbs are checked with the deck and its PTO unit fitted, since mowing a slope
is the design case ([design review](reviews/initial-design-review.md)).

- **Grip sets the rating.** With the deck's weight between the axles, the rear
  tyres grip up to about 14° on turf (traction 0.5), whatever the ratio. Rear
  ballast that restored grip at 15° (~40 kg) would push the torque past the
  motor's peak, so Home is rated for 12° short climbs. The AWD Pro keeps 15°.
- **The 15:1 gear set is standard** (`"axle.ratio" = 15.0` in
  `design/models/home.toml`; BOM G01). On the stock set a 12° climb sits right
  at the ~4× peak.

The torque each motor needs, as a multiple of its rated torque:

| Rear end | 10° climb | 12° short climb |
|---|---|---|
| Stock 12.4:1 | 3.6× (heats on long climbs) | 4.0×, at the peak |
| **Stock + aftermarket 15:1 gear set** (standard) | 3.0× | 3.3× |
| Stock + 2:1 chain stage | 1.8× | 2.1× |

## EOX Pro: articulated AWD

```
        rear half                 hinge zone ±160 mm                 front half
  seat + operator           knuckle ┃● ┃ clevis ears            battery & distribution box
  ─[controller]─[rear axle + motor]═neck═┃●┃═neck═[front axle + motor]─[controller]── implement face
                            trunnion ┃  ┃  cylinder: front frame → knuckle
```

**Drive-axle module.**

- A golf-cart rear end with one 3 HP unit.
- As on a real cart, the motor axis is parallel to the axle. The motor sits on
  the side of the off-centre gear case, above the axle centre.
- The controller lies flat on a cross member outboard of the axle, on the
  centreline.
- The module is clamped to sheet-steel rails at ±310 mm with U-bolts, which
  also stop the housing rotating.

**Centre pivot.**

- **Hinge zone:** each half-frame necks in from ±310 mm to ±170 mm and ends in
  a cross member 160 mm from the pivot.
- **Front clevis:** ears carry upper and lower 25 mm pins, 220 mm apart, in
  spherical plain bearings. They allow yaw to ±40° bump stops.
- **Rear knuckle:** yaws with the rear half and rides on a fore-aft roll
  trunnion, so the halves roll ±10° relative to each other and all four wheels
  stay on the ground.
- **Ears:** laser-cut flat from 1/2 in steel, since SendCutSend bends steel
  only to 0.25 in.
- **Frame lock:** a red bar locks the joint for transport and service.
- **Pitch is locked,** so the halves share fore-aft loads.
- **Checked:**
  - at ±40° no front-half part touches a rear-half part;
  - the front half stays 231 mm from the operator's footwell;
  - each pin sees 5 kN at 3 g, far inside its strength. Pin size is set by
    wear and stiffness.
- **Still open:** the detail design (pins, bearings, stops, lock bar) is
  [issue 5](https://github.com/zacharyelston/EOx/issues/5), informed by
  [docs/research/articulation.md](research/articulation.md).

**Mass.**

- 305 kg without the operator; 371 kg with the front-mount deck and its PTO
  unit.
- The axle split with the operator is 43 / 57 (front / rear), and 58 / 42 with
  the deck fitted.

**Stability (static).**

| | Tip angle |
|---|---|
| Whole machine | 48° straight, 44° at full lock |
| Front half's triangle (its wheels + pivot) | 54° |
| Rear half's triangle | 40° |
| Half the lowest, used as the max working slope | 20.2° (design slope 15°) |

Each is the worse of bare and deck-fitted. These are industry practice, not
values confirmed from B71.1.

**Steering.**

- Articulating at a standstill needs about 1,050 N·m with the front deck
  fitted (about 880 N·m bare), because the tyres scrub sideways.
- One 45 mm cylinder at 100 bar runs from the front frame to a steering arm on
  the knuckle, so roll can't steer the machine. On a 120 mm lever arm it gives
  1,173 N·m at full lock (WARN: a 12 % margin with the deck) and goes lock to
  lock in 3.3 s, from a small 48 V power unit.
- An 8 kN electric actuator would take ~15 s lock to lock, which is too slow.
- A manual chain-and-wire-rope linkage (Stiga / Husqvarna style) would need
  ~280 N at the rim at a standstill (est.).
- The outer turning radius is 2.4 m.

**Gearing.** EOX uses stock golf-cart rear ends (~12.4:1), which are geared for 25 km/h; the controller limits speed to 8 km/h.

| Option | Torque per motor on a sustained 10° climb |
|---|---|
| Stock (default) | 2.1× rated, deck fitted (WARN: fine short, heats on long climbs) |
| Aftermarket 15:1 gear set | 1.7× rated |
| ~2:1 chain stage added | 1.1× rated |

## Attachments

**Mower deck.**

- The deck carries its own PTO unit, so the coupling is mechanical plus one
  connector, not a shaft.
- **Where it mounts follows from the front axle.**
  - A golf-cart diff hangs 114 mm (4.5 in) above the ground, which is 36 mm
    *lower* than the top of a typical deck at its lowest cut height, so the
    Pro's front axle can't roll over a deck. The Pro's deck is front-mounted on
    the implement face.
  - The Home's beam front axle has no diff and clears a mid-mount deck.
  - The mass model carries the deck (45 kg, REF) and its PTO unit at those
    positions whenever it is fitted. The coupling design is still open.
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
