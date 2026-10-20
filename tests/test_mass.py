"""Mass reconciliation (review P1, docs/reviews/initial-design-review.md).

The vehicle model must carry every configured component, the mower deck and
its PTO unit included, and every mass-dependent check must use the deck-fitted
figure (drive) or the worse of bare and deck-fitted (stability, steering)."""
import math

import pytest

from eox import calcs, tractor
from eox.calcs.drive import _per_motor
from eox.calcs.vehicle import CONFIGS, stability
from eox.params import load
from eox.tractor import DECK

MODELS = ["home", "pro"]


@pytest.fixture(scope="module", params=MODELS)
def model(request):
    p = load(request.param)
    tr = tractor.build(p)
    return p, tr, calcs.run(p, tr)


def _check(rep, prefix):
    return next(c for c in rep.checks if c.name.startswith(prefix))


def _expected_bare_kg(p, tr) -> float:
    """Sum the configured component masses straight from the parameter files."""
    a, u, lo = p.axle, p.unit, p.layout
    drive_module = 2 * a.wheel_tire_mass_kg + a.rear_end_mass_kg + u.motor_mass_kg + u.controller_mass_kg
    box = sum(kg for _, kg, _ in tr.box.mass_items())
    people = p.vehicle.mass_operator_kg + p.vehicle.mass_payload_kg
    if tr.articulated:
        rest = (2 * (drive_module + a.subframe_mass_kg) + lo.joint_mass_kg + lo.steering_mass_kg
                + lo.implement_mass_kg)
    else:
        s = p.steer_axle
        rails_m = 2 * (lo.nose_x + lo.rear_overhang + lo.wheelbase + lo.front_overhang - lo.nose_x) / 1000
        rest = drive_module + rails_m * lo.rail_mass_kg_per_m + s.mass_kg + 2 * s.wheel_tire_mass_kg + lo.hitch_mass_kg
        parts = {b.name for _, _, b in tr.bodies}
        rest += lo.box_stand_mass_kg * ("box stand" in parts) + lo.seat_pedestal_mass_kg * ("seat pedestal" in parts)
    return rest + box + lo.seat_and_controls_mass_kg + people


def _deck_kg(p) -> float:
    return p.deck.mass_kg + p.unit.motor_mass_kg + p.unit.controller_mass_kg


def test_machine_mass_reconciles_to_configured_components(model):
    p, tr, _ = model
    assert tr.mass() == pytest.approx(_expected_bare_kg(p, tr))
    assert tr.mass(fitted=DECK) - tr.mass() == pytest.approx(_deck_kg(p))


def test_a_front_mounted_box_still_reconciles():
    """Moving Home's box over the front axle adds a stand under it and a pedestal under the seat."""
    p = load("home", {"layout.powerbox_x": 1600, "layout.powerbox_z": 500})
    tr = tractor.build(p)
    parts = {b.name for _, _, b in tr.bodies}
    assert {"box stand", "seat pedestal"} <= parts
    assert tr.mass() == pytest.approx(_expected_bare_kg(p, tr))


def test_reported_machine_mass_is_bare_and_deck_fitted(model):
    p, tr, rep = model
    people = p.vehicle.mass_operator_kg + p.vehicle.mass_payload_kg
    bare, fitted = (float(x) for x in _check(rep, "machine mass (no operator)").value.split(" / "))
    assert bare == pytest.approx(_expected_bare_kg(p, tr) - people, abs=0.5)
    assert fitted - bare == pytest.approx(_deck_kg(p), abs=1)


def test_deck_sits_where_the_model_mounts_it(model):
    p, tr, _ = model
    decks = [(g, b) for g, k, b in tr.bodies if k == "deck"]
    assert len(decks) == 1
    group, deck = decks[0]
    front, rear = tr.axle("front").x, tr.axle("rear").x
    if tr.articulated:                     # Pro: front-mount, carried by the front half ahead of its axle
        assert group == "front" and deck.center[0] > front
    else:                                  # Home: mid-mount, between the axles
        assert rear < deck.center[0] < front
    assert any(k == "pto" for _, k, _ in tr.bodies)


def test_the_deck_moves_load_towards_where_it_hangs(model):
    _, tr, _ = model
    share = {f: tr.axle_loads_n(fitted=f)["front"] / (tr.mass(fitted=f) * 9.81) for f in CONFIGS}
    assert share[DECK] > share[()]         # both decks sit ahead of the bare CG


def test_climb_checks_use_the_deck_fitted_mass(model):
    p, tr, rep = model
    slope = p.vehicle.max_slope_deg
    t_fitted, t_bare = _per_motor(p, tr, slope), _per_motor(p, tr, slope, fitted=())
    assert t_fitted == pytest.approx(_per_motor(p, tr, slope, fitted=DECK))
    assert t_fitted / t_bare == pytest.approx(tr.mass(fitted=DECK) / tr.mass())    # torque scales with mass
    assert _check(rep, f"motor torque each, {slope:g} deg climb, deck fitted").value == round(t_fitted, 1)


def test_stability_reports_the_worse_of_bare_and_deck_fitted(model):
    p, tr, rep = model
    angles = [0.0] + ([p.layout.articulation_max_deg] if tr.articulated else [])
    worst = min(v for g in angles for f in CONFIGS for v in stability(tr, g, f).values())
    assert _check(rep, "max working slope").value == pytest.approx(worst / 2, abs=0.05)


def test_home_deck_turns_a_stock_15_degree_climb_from_warn_to_fail():
    """The review's headline: on the stock 12.4:1 rear end the bare Home
    climbs 15 deg inside peak torque, but not with its 45 kg deck and PTO
    unit. (Home now ships with the 15:1 gear set and a 12 deg rating.)"""
    p = load("home")
    tr = tractor.build(p)
    u = p.unit
    peak = u.rated_power_w / (2 * math.pi * u.base_speed_rpm / 60) * u.peak_torque_factor
    stock = 12.4
    assert _per_motor(p, tr, 15, ratio=stock, fitted=()) <= peak < _per_motor(p, tr, 15, ratio=stock)
