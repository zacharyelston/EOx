"""Reference machines on the course: within their makers' ratings they must
not fail. If one does, its model is wrong (the real machine does it), so fix
the estimates in design/reference/ rather than the test."""
import pytest

from eox import reference


@pytest.mark.parametrize("name", ["deere-x350", "husqvarna-r316tx-awd"])
def test_a_reference_does_what_its_maker_rates_it_for(name):
    out = reference.evaluate(name)
    m = out["metrics"]
    assert m["grip_limit_deg"] >= m["rated_slope_deg"]
    fails = [o.name for o in out["runs"][0].obstacles if o.status == "FAIL"]
    assert not fails, fails
