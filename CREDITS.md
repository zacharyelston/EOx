# Credits

## Third-party assets

None bundled yet. Each one added under `assets/third_party/` gets a line here:
name, author, licence, source URL. Rules: [assets/README.md](assets/README.md).

## Software EOX builds on

Installed by `uv`, not bundled; each keeps its own licence.

| Package | Licence | Used for |
|---|---|---|
| [build123d](https://github.com/gumyr/build123d) (OpenCascade) | Apache-2.0 (OCCT: LGPL-2.1 with exception) | CAD solids, STEP export |
| [ezdxf](https://github.com/mozman/ezdxf) | MIT | DXF flat patterns |
| [MuJoCo](https://mujoco.org) | Apache-2.0 | Terrain-course physics and renders |
| [NumPy](https://numpy.org) | BSD-3-Clause | Numerics |
| [Pillow](https://python-pillow.org) | MIT-CMU | Course render strips and GIFs |

## Data and research

Published specifications for the reference machines (John Deere, Cub Cadet,
Ryobi, Husqvarna, Tuff Torq) are cited, source by source, in each file in
`design/reference/`; golf-cart geometry in `docs/research/golf-cart.md`;
articulated-steering research in `docs/research/articulation.md`. Trademarks
belong to their owners and are used only to identify the machines compared.
