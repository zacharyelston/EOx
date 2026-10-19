# Review: `initial-design`

Reviewed `origin/main...initial-design` at `1cb4be6`.

## Finding

### [P1] Include the mower deck in vehicle mass properties

Both model files specify a 45 kg mower deck (`design/models/home.toml:52-56` and
`design/models/pro.toml:75-79`), and the operating-mode calculations model the
deck running while mowing. Neither `build_home` nor `build_pro` adds that mass
to `Tractor.masses`, however (`src/eox/tractor.py:243-257` and
`src/eox/tractor.py:290-307`). The drive calculation then derives climb torque
from `tr.mass()` (`src/eox/calcs/drive.py:24`), while axle loads, stability,
steering effort, and the reported machine mass use the same incomplete mass
model.

This is already decision-changing for Home. The current report gives 23.3 N·m
per motor on the 15° climb against a 23.8 N·m peak limit. Adding the omitted
45 kg, even before accounting for its position, scales that result to about
26.4 N·m and changes the check from WARN to FAIL. For Pro, the missing deck
also changes the front/rear-half mass split and tip angles, so its actual
mounting location must be represented rather than adding the mass at an
arbitrary CG.

Add the deck (including its PTO unit, or document that the stated mass already
includes it) to each applicable builder at a model-specific CG. Add a test
that the reported machine mass reconciles to all configured components and a
regression test for the resulting climb/stability checks.

## Validation performed

- `uv run pytest -q`: 39 passed.
- `git diff --check origin/main...HEAD`: no whitespace errors (run before this
  review file was added).
- Independently reconciled each builder's `Tractor.masses` entries against the
  model mass parameters and recalculated the Home peak-torque effect above.

## Residual risk

The repository describes several component dimensions, ratings, and safety
limits as reference or unconfirmed values. This review checked code and model
consistency; it does not validate those engineering assumptions against vendor
data, physical measurements, or the cited standards.
