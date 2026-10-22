"""Engineering checks for an EOX model, one module per domain:

    bus       48 V bus: SELV, unit branches, main protection, operating modes
    drive     golf-cart axle modules: torque, speed, traction, gearing options
    vehicle   mass split, stability, turning, steering, pinch zone
    powerbox  battery & distribution box: fit, SCS rules, thermal, structure
"""

from __future__ import annotations

from eox.calcs import bus, drive, powerbox, vehicle
from eox.calcs.common import Report

__all__ = ["Report", "run"]


def run(p, tr) -> Report:
    r = Report()
    bus.run(p, tr, r)            # first: sets the mode currents the box thermal check uses
    drive.run(p, tr, r)
    vehicle.run(p, tr, r)
    powerbox.run(p, tr.box, r)
    if hasattr(p, "kit"):
        from eox.checks import Check
        r.add(Check("Kit study", "all layer blank envelopes fit their reference sheets",
                    p.kit.nest_fails, "layers without fit", 0, "<=",
                    note="provisional inventory; not joint/tooling/structural approval"))
    return r
