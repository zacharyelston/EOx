# Research: how small articulated machines build the centre joint

Collected 2026-10-18 to design the EOX Pro pivot
([issue 5](https://github.com/zacharyelston/EOx/issues/5)). Every fact cites its
source; **(est.)** marks an engineering estimate, not a published number.

**Not published by any OEM we found:** hinge-pin diameters or bearing part
numbers. Goldoni, MultiOne and Pasquali/Ferrari joint angles were not found
either.

## What real machines do

| Machine | Hinge | Oscillation (roll) | Steering | Lock / radius |
|---|---|---|---|---|
| Antonio Carraro ACTIO (Tigre, SRX) | Cast central joint [1] | In the joint, up to 15° [1] | Hydraulic, articulated frame [3] | Operator sits on the oscillation centre [2] |
| BCS OS-Frame "AR" | One casting; a universal joint carries the drive across [4] | Front oscillates up to 15° vs the rear [4] | Acts on the central joint [4] | n/a |
| Husqvarna Rider 11/13/16 | Separate upper and lower articulation bearings [5, p36] | Rear frame on a fore-aft swing axle in bushings [5, p37] | Wheel → chain → wire ropes to the rear section, manual [5, p21] | Uncut circle 20–30 cm [5, p21] |
| Husqvarna R320X AWD | n/a | n/a | n/a | 88.7 cm wheelbase, 30 cm uncut circle [6] |
| Stiga Park | n/a | n/a | Column sprocket → chain → wires to a steering disc on the rear frame, spring adjusters [9, p40–43]. 2WD versions add a small hydraulic assist [9, p40] | 375 kg Park Pro 900 WX uses power steering [10] |
| Avant | Rigid joint, no sideways pivot [12] | None | n/a | Operator on the front part [13] |
| Schäffer (small loaders) | Maintenance-free oscillating articulated joint [14] | In the joint (big models move it to the rear axle) [14] | 8620 T-2: two cylinders [14] | n/a |
| Mustang 608/708 | Oscillating articulation joint [16] | ±10° [16] | n/a | ±45° [16] |
| Cat 908 (6.6 t) | n/a | ±11° at the hitch [17] | 2.8 s and 3.25–4.0 wheel turns lock to lock [17] | ±39° [17] |

**Wheel-loader practice:**

- **Pins:** upper and lower hitch pins with tapered rollers; the lower pin takes
  most of the load [19].
- **Ball-type hinge bearings:** allow for misalignment between the upper and
  lower bores [20].
- **Frame lock:** a lock bar for transport and service is standard [21].

**DIY builds:** one used two cylinders plumbed push-pull, one each side of the
joint, to balance the load on it [22]. Another used a 1½ in pin and a single
cylinder [23].

**Standards:**

- **EN ISO 13854 minimum gaps to avoid crushing:** body 500, head 300, leg 180,
  foot 120, arm 120, hand 100, toes 50, finger 25 mm [24].
- **ISO 10570:2004:** performance requirements for an articulated-frame lock
  [25]; it replaced SAE J276 [26].
- **ISO 5395-3:** excludes battery mowers [27].

## What EOX Pro adopts

| Decision | Choice | Why |
|---|---|---|
| Joint | Front-half **clevis** with upper and lower vertical pins, about 220 mm apart, into a **knuckle** that carries a fore-aft **roll trunnion** into the rear half | Golf-cart axles are rigid, so roll has to live in the joint, as on small Schäffer, Mustang and Cat machines [14][16][17]. A rigid joint like Avant's [12] would lift wheels and lose AWD traction on lawns. |
| Pins and bearings | 25 mm hardened pins in greasable spherical plain bearings (GE25ES class: C₀ 334 kN [29]), clamped in the ears | Spherical bearings forgive bore misalignment between laser-cut ears [20]. Pin size is set by wear and stiffness, not strength (`Pivot` checks). |
| Oscillation | ±10° with rubber stops; trunnion about 40 mm in two bushings ≥ 150 mm apart (est.) | Matches Mustang and Cat [16][17] |
| Articulation | **±40°** to bump stops that engage before the cylinder bottoms | Peers run 39–45° [16][17]. Outer turning radius drops from 2.6 m to about 2.3 m. |
| Steering | One cylinder from the **front frame to the knuckle**, so roll of the rear half can't steer the machine. Two push-pull cylinders are the alternative [21][22]. | Hydraulic, as Stiga does at 375 kg [10] |
| Manual option | Not for Pro. A Stiga/Husqvarna-style chain and wire-rope sector [5][9] would need ~280 N at the rim to steer at a standstill (est.) | Only practical while rolling |
| Frame lock | Laser-cut 10 mm bar pinned between lugs on both halves, painted red, stowed on the frame | ISO 10570 / SAE J276 practice [25][26] |
| Operator | Seat and feet both on the rear half, near the joint. Footwell ≥ 120 mm from any moving edge; ≥ 500 mm wherever a body could be, or guard it. | ISO 13854 [24]; Carraro seats the operator on the oscillation centre [2] |
| Making the clevis | Ears **laser-cut flat** from 3/8–1/2 in steel; bolt them through the frame webs with doublers, or tab-and-slot weld them. Bore undersize, then ream after welding. | SendCutSend bends mild steel only to 0.250 in [30], but laser-cuts to 0.500 in [31] |

## Sources

1. https://www.antoniocarraro.it/en/plus/actio
2. https://www.antoniocarraro.it/en/catalogue/tigrecar-gst
3. https://www.antoniocarraro.it/en/catalogue/srx-ergit-r
4. https://bcsagri.com/en-150/technology/os-frame-chassis/
5. https://www.manualslib.com/manual/716829/Husqvarna-Rider-13.html
6. https://www.husqvarna.com/uk/ride-on-front-mowers/r320x-awd
9. https://www.manualslib.com/manual/2421994/Stiga-Park-Series.html
10. https://www.landwirt.com/detail/stiga-park-pro-900-wx-inkl-maehdeck-3935014
12. https://cdn.base.parameter1.com/files/base/acbm/fcp/document/2013/04/avant-product-overview-brochur_10924988.pdf
13. https://blog.noltspower.com/?p=308
14. https://www.schaeffer.de/wp-content/uploads/Gesamt_Landwirtschaft_DE_2306.pdf
16. https://www.constructionequipmentguide.com/mustang-increases-product-breadth-with-new-articulated-loaders-for-north-america/29165
17. https://www.toromontcat.com/new-attachments/compact-wheel-loaders/116320-908
19. https://patents.google.com/patent/US5961141
20. https://patents.google.com/patent/US4192523
21. https://open-exam-prep.com/study-guides/nccer-heavy-equipment/loaders/wheel-loader-anatomy-linkage (secondary)
22. https://www.farmshow.com/a_article.php?aid=23297
23. https://farmshow.com/view_articles.php?a_id=1338
24. https://medien.bgetem.de/medienportal/artikel/UzA0NC1F/@@download/download
25. https://intertekinform.com/en-us/standards/iso-10570-2004-593977_saig_iso_iso_1360615/
26. https://saemobilus.sae.org/standards/j276_200801-steering-frame-lock-articulated-loaders-tractors
27. https://www.evs.ee/en/iso-5395-3-2013
29. https://www.acorn-ind.co.uk/p/iko/radial-spherical-plain-bearings/ge25es-2rs-iko/
30. https://sendcutsend.com/bending/
31. https://sendcutsend.com/materials/mild-steel/
