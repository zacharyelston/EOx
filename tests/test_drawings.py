import re
import xml.etree.ElementTree as ET

import pytest

from eox import drawings, tractor
from eox.params import ROOT, load

NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def pro():
    p = load("pro")
    return p, tractor.build(p)


@pytest.mark.parametrize("theme", list(drawings.THEMES))
def test_cut_diagrams_show_every_hole_and_bend(pro, theme):
    _, tr = pro
    for part in tr.box.parts:
        root = ET.fromstring(drawings.flat_svg(part, theme))
        dashed = [e for e in root.iter(f"{NS}line") if e.get("stroke-dasharray")]
        assert len(dashed) - 1 * bool(part.flanges) == len(part.flanges)   # bend lines (+ the legend key)
        round_holes = sum(1 for h in part.holes if not h.length)
        legend_circles = len({(h.label, h.d) for h in part.holes if not h.length})
        assert len(list(root.iter(f"{NS}circle"))) == round_holes + legend_circles


@pytest.mark.parametrize("theme", list(drawings.THEMES))
def test_figures_are_valid_svg(pro, theme):
    p, tr = pro
    for svg in (drawings.stability_svg(tr, theme), drawings.modes_svg(p, tr, theme)):
        root = ET.fromstring(svg)
        assert root.find(f"{NS}title") is not None and root.find(f"{NS}desc") is not None


def test_readme_images_exist():
    text = (ROOT / "README.md").read_text()
    refs = re.findall(r'(?:src|srcset)="([^"]+)"', text) + re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    missing = [r for r in refs if not r.startswith("http") and not (ROOT / r).exists()]
    assert refs and not missing
