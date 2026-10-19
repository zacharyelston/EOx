"""Figures for the README and docs, as SVG in a light and a dark variant.

    flat_svg       SendCutSend cut diagram for one sheet-metal part
    stability_svg  plan view of the support polygons and centres of gravity
    modes_svg      average battery power by operating mode

Colours are the dataviz reference palette: categorical slots 1-5 (validated
for light and dark surfaces) and its chart chrome. Every figure is drawn from
the same objects the CAD and the calcs use, so it can't drift from the design.
"""

from __future__ import annotations

import math
from collections import Counter
from html import escape

from eox.sheetmetal import IN, FlangedPanel

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  base="#c3c2b7", series=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 base="#383835", series=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]),
}
FONT = 'system-ui, -apple-system, &quot;Segoe UI&quot;, sans-serif'


class Svg:
    """Tiny SVG builder in pixel units."""

    def __init__(self, w: float, h: float, theme: str):
        self.w, self.h, self.t, self.el = w, h, THEMES[theme], []

    def add(self, s: str):
        self.el.append(s)

    def text(self, x, y, s, size=12, fill=None, anchor="start", weight=400, rotate=None):
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill or self.t["ink"]}" '
                 f'text-anchor="{anchor}"{tr}>{escape(str(s))}</text>')

    def line(self, x1, y1, x2, y2, stroke, width=1.0, dash=None, cap="butt"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{width}" stroke-linecap="{cap}"{d}/>')

    def render(self, title: str, desc: str) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" '
                f'width="{self.w:.0f}" height="{self.h:.0f}" role="img" aria-labelledby="t d" '
                f'font-family="{FONT}">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
                f'<rect width="100%" height="100%" rx="8" fill="{self.t["surface"]}"/>\n'
                + "\n".join(self.el) + "\n</svg>\n")


# ---------------------------------------------------------------------------
# Flat-pattern cut diagram
# ---------------------------------------------------------------------------
def _outline_segments(rects):
    """Outline of a union of axis-aligned rectangles, as merged segments."""
    xs = sorted({v for r in rects for v in (r[0], r[2])})
    ys = sorted({v for r in rects for v in (r[1], r[3])})

    def covered(i, j):
        if not (0 <= i < len(xs) - 1 and 0 <= j < len(ys) - 1):
            return False
        cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects)

    vert, horiz = {}, {}
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if not covered(i, j):
                continue
            if not covered(i - 1, j):
                vert.setdefault(xs[i], []).append((ys[j], ys[j + 1]))
            if not covered(i + 1, j):
                vert.setdefault(xs[i + 1], []).append((ys[j], ys[j + 1]))
            if not covered(i, j - 1):
                horiz.setdefault(ys[j], []).append((xs[i], xs[i + 1]))
            if not covered(i, j + 1):
                horiz.setdefault(ys[j + 1], []).append((xs[i], xs[i + 1]))

    def merge(spans):
        spans = sorted(spans)
        out = [list(spans[0])]
        for a, b in spans[1:]:
            if abs(a - out[-1][1]) < 1e-6:
                out[-1][1] = b
            else:
                out.append([a, b])
        return out

    segs = [((x, a), (x, b)) for x, sp in vert.items() for a, b in merge(sp)]
    segs += [((a, y), (b, y)) for y, sp in horiz.items() for a, b in merge(sp)]
    return segs


def _arrow(s: Svg, x1, y1, x2, y2, color, label, size=12, vertical=False):
    """Dimension line with arrowheads and a centred label."""
    s.line(x1, y1, x2, y2, color, 1)
    ang = math.atan2(y2 - y1, x2 - x1)
    for (x, y), a in (((x1, y1), ang), ((x2, y2), ang + math.pi)):
        p1 = (x + 7 * math.cos(a + 0.35), y + 7 * math.sin(a + 0.35))
        p2 = (x + 7 * math.cos(a - 0.35), y + 7 * math.sin(a - 0.35))
        s.add(f'<path d="M{x:.1f},{y:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{color}"/>')
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if vertical:
        s.text(mx - 8, my, label, size, s.t["ink2"], "middle", rotate=-90)
    else:
        s.text(mx, my - 6, label, size, s.t["ink2"], "middle")


def flat_svg(part: FlangedPanel, theme: str, qty: int = 1) -> str:
    t = THEMES[theme]
    rects = part.flat_rects()
    x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
    x1, y1 = max(r[2] for r in rects), max(r[3] for r in rects)
    W, H = x1 - x0, y1 - y0
    groups = Counter((h.label or "hole", h.d, h.length) for h in part.holes)
    legend_rows = len(groups) + (1 if part.flanges else 0)
    draw_w = min(max(W * 0.72, 480), 820)               # small parts drawn larger so labels fit
    sc = draw_w / W
    left, right, top = 56, 28, 92
    bottom = 54 + 20 * legend_rows
    s = Svg(max(left + draw_w + right, 620), top + H * sc + bottom, theme)
    X = lambda x: left + (x - x0) * sc                    # noqa: E731
    Y = lambda y: top + (y1 - y) * sc                     # noqa: E731

    # title block
    bends = len(part.flanges)
    s.text(16, 26, f"{part.part_no} · {part.name}", 16, weight=600)
    s.text(16, 46, f"{part.g.material} {part.g.t / IN:.3f} in ({part.g.t:.2f} mm) · {bends} bend{'s' * (bends != 1)}"
           f" · qty {qty} · {part.mass_kg():.2f} kg each", 12, t["ink2"])
    s.text(16, 64, f"SendCutSend K {part.g.k:g}, inside radius {part.g.r / IN:.3f} in. Order the STEP; "
           "this flat is the reference cut.", 11, t["muted"])

    # sheet: one path so adjacent rectangles fill without seams
    d = " ".join(f"M{X(r[0]):.2f},{Y(r[3]):.2f} H{X(r[2]):.2f} V{Y(r[1]):.2f} H{X(r[0]):.2f} Z" for r in rects)
    s.add(f'<path d="{d}" fill="{t["series"][0]}" fill-opacity="0.10"/>')
    for (ax, ay), (bx, by) in _outline_segments(rects):
        s.line(X(ax), Y(ay), X(bx), Y(by), t["ink"], 1.5, cap="square")

    # bend lines, labelled on the flange side
    for edge, ((ax, ay), (bx, by)) in zip(part.flanges, part.bend_lines()):
        s.line(X(ax), Y(ay), X(bx), Y(by), t["series"][0], 1.5, dash="9 5")
        mx, my = (X(ax) + X(bx)) / 2, (Y(ay) + Y(by)) / 2
        out = 1 if edge[0] == "+" else -1                     # which side the flange unfolds to
        if edge[1] == "u":                                    # vertical bend line
            ly = min(Y(ay), Y(by)) + 0.18 * abs(Y(ay) - Y(by))  # near the end: glands sit mid-flange
            s.text(mx + out * 14 + (4 if out > 0 else 0), ly, "fold up 90°", 10, t["ink2"], "middle", rotate=-90)
        else:                                                 # horizontal: +v unfolds upward (SVG y down)
            s.text(mx, my - 6 if out > 0 else my + 14, "fold up 90°", 10, t["ink2"], "middle")

    # holes and slots
    for h in part.holes:
        cx, cy = part.flat_point(h)
        r = h.d / 2 * sc
        if h.length:
            L = h.length * sc
            w, hh = (L + 2 * r, 2 * r) if part._along_flat_x(h) else (2 * r, L + 2 * r)
            s.add(f'<rect x="{X(cx) - w / 2:.1f}" y="{Y(cy) - hh / 2:.1f}" width="{w:.1f}" height="{hh:.1f}" rx="{r:.1f}" '
                  f'fill="{t["surface"]}" stroke="{t["ink"]}" stroke-width="1"/>')
        else:
            s.add(f'<circle cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="{max(r, 1.2):.1f}" fill="{t["surface"]}" '
                  f'stroke="{t["ink"]}" stroke-width="1"/>')

    # overall dimensions
    yb = Y(y0) + 22
    s.line(X(x0), Y(y0) + 4, X(x0), yb + 4, t["base"], 1)
    s.line(X(x1), Y(y0) + 4, X(x1), yb + 4, t["base"], 1)
    _arrow(s, X(x0), yb, X(x1), yb, t["muted"], f"{W:,.0f} mm ({W / IN:.2f} in)")
    xl = left - 22
    s.line(left - 4, Y(y1), xl - 4, Y(y1), t["base"], 1)
    s.line(left - 4, Y(y0), xl - 4, Y(y0), t["base"], 1)
    _arrow(s, xl, Y(y1), xl, Y(y0), t["muted"], f"{H:,.0f} mm", vertical=True)

    # legend
    ly = Y(y0) + 54
    if part.flanges:
        s.line(16, ly - 4, 44, ly - 4, t["series"][0], 1.5, dash="9 5")
        s.text(52, ly, "bend line: fold up 90°, toward you", 11, t["ink2"])
        ly += 20
    for (label, dia, length), n in sorted(groups.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        if length:
            s.add(f'<rect x="20" y="{ly - 10:.1f}" width="20" height="8" rx="4" fill="{t["surface"]}" stroke="{t["ink"]}"/>')
            size = f"slot {dia:g} x {length + dia:g}"
        else:
            s.add(f'<circle cx="30" cy="{ly - 4:.1f}" r="5" fill="{t["surface"]}" stroke="{t["ink"]}"/>')
            size = f"Ø{dia:g}"
        s.text(52, ly, f"{size} mm × {n}   {label}", 11, t["ink2"])
        ly += 20
    return s.render(f"{part.part_no} flat pattern", f"Cut diagram for {part.name}: outline, holes and bend lines, "
                    f"flat size {W:.0f} by {H:.0f} mm.")


# ---------------------------------------------------------------------------
# Stability plan view
# ---------------------------------------------------------------------------
def stability_svg(tr, theme: str) -> str:
    """Plan view: support polygons, pivot and CGs, mowing configuration (deck
    fitted). Pro: straight + full lock, with each half's triangle. Home: one
    panel, four wheels."""
    from eox.calcs.vehicle import stability
    from eox.tractor import DECK

    t = THEMES[theme]
    p = tr.p
    gammas = [0.0, p.layout.articulation_max_deg] if tr.articulated else [0.0]
    sc = 0.21
    xs = [ax.x for ax in tr.axles]
    tire = max(ax.tire_diameter for ax in tr.axles)
    x_lo, x_hi = min(xs) - tire / 2 - 150, max(xs) + tire / 2 + 250
    span_y = max(ax.track + ax.tire_width for ax in tr.axles) + (900 if tr.articulated else 300)
    pw, ph = (x_hi - x_lo) * sc, span_y * sc
    s = Svg(len(gammas) * (pw + 20) + 40, ph + 112, theme)
    items = [(0, "whole machine on 4 wheels")]
    if tr.articulated:
        items += [(1, "front half triangle"), (2, "rear half triangle")]
    s.text(16, 26, f"{p.model.name}: static stability, plan view, mowing (deck fitted)", 16, weight=600)
    lx = 16
    for i, label in items:
        s.add(f'<rect x="{lx}" y="40" width="14" height="10" rx="2" fill="{t["series"][i]}" fill-opacity="0.15" '
              f'stroke="{t["series"][i]}" stroke-width="2"/>')
        s.text(lx + 20, 49, label, 11, t["ink2"])
        lx += 30 + 6.2 * len(label)
    s.add(f'<circle cx="{lx + 6}" cy="45" r="5" fill="{t["ink"]}" stroke="{t["surface"]}" stroke-width="2"/>')
    s.text(lx + 16, 49, "centre of gravity" + (" (machine, front, rear)" if tr.articulated else " with operator"), 11, t["ink2"])

    def poly(pts, P, **kw):
        attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        s.add('<polygon points="' + " ".join(f"{P(q)[0]:.1f},{P(q)[1]:.1f}" for q in pts) + f'" {attrs}/>')

    def rot(pts, g):
        return [(x * math.cos(g) - y * math.sin(g), x * math.sin(g) + y * math.cos(g)) for x, y in pts]

    for k, gamma in enumerate(gammas):
        ox, oy = 20 + k * (pw + 20), 70
        cx0, cy0 = ox - x_lo * sc, oy + 30 + ph / 2
        P = lambda pt, cx0=cx0, cy0=cy0: (cx0 + pt[0] * sc, cy0 - pt[1] * sc)   # noqa: E731
        res = stability(tr, gamma, DECK)
        if tr.articulated:
            s.text(ox, oy + 6, "straight" if not gamma else f"full lock {gamma:g}°", 13, weight=600)
            sub = f"tip angles: rigid {res['rigid']:.0f}° · front {res['front']:.0f}° · rear {res['rear']:.0f}°"
        else:
            sub = f"tip angle {res['rigid']:.0f}° in the worst direction"
        s.text(ox, oy + 24, sub, 11, t["ink2"])
        # context: tyres, box and seat outlines
        for ax in tr.axles:
            g = math.radians(gamma) if (tr.articulated and ax.group == "front") else 0.0
            for c in tr.contacts(ax.name, gamma):
                hl, hw = ax.tire_diameter / 2, ax.tire_width / 2
                foot = [(c[0] + dx * math.cos(g) - dy * math.sin(g), c[1] + dx * math.sin(g) + dy * math.cos(g))
                        for dx, dy in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]
                poly(foot, P, fill=t["grid"], stroke=t["base"], stroke_width=1)
        L, Wb, _ = tr.box.outer
        bx = tr.box_pos[0]
        gb = math.radians(gamma) if (tr.articulated and tr.box_group == "front") else 0.0
        box = rot([(bx + sx * L / 2, sy * Wb / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))], gb)
        poly(box, P, fill="none", stroke=t["muted"], stroke_width=1)
        bl = P(rot([(bx, Wb / 2 + 40)], gb)[0])
        s.text(bl[0], bl[1], "power box" + ("" if tr.articulated else " + seat"), 10, t["muted"], "middle")
        if tr.articulated:
            sx_, sz = p.layout.operator_cg[0], 220
            poly([(sx_ - sz, -sz), (sx_ + sz, -sz), (sx_ + sz, sz), (sx_ - sz, sz)], P, fill="none",
                 stroke=t["muted"], stroke_width=1)
            sl = P((sx_, sz + 40))
            s.text(sl[0], sl[1], "seat", 10, t["muted"], "middle")
        # support polygons
        fl, fr = tr.contacts("front", gamma)
        rl, rr = tr.contacts("rear", gamma)
        polys = [([fl, fr, rr, rl], 0)]
        if tr.articulated:
            j = tr.joint()
            polys += [([fl, fr, j], 1), ([rl, rr, j], 2)]
        for pts, i in polys:
            poly(pts, P, fill=t["series"][i], fill_opacity="0.10", stroke=t["series"][i], stroke_width=2,
                 stroke_linejoin="round")
        dots = [(None, t["ink"])]
        if tr.articulated:
            jx, jy = P(tr.joint())
            s.add(f'<circle cx="{jx:.1f}" cy="{jy:.1f}" r="4" fill="{t["surface"]}" stroke="{t["ink"]}" stroke-width="1.5"/>')
            s.text(jx, jy - 9, "pivot", 10, t["ink2"], "middle")
            dots += [("front", t["series"][1]), ("rear", t["series"][2])]
        for group, fill in dots:              # 2 px surface ring
            x, y = P(tr.cg(group, gamma, DECK))
            s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{fill}" stroke="{t["surface"]}" stroke-width="2"/>')
        ax_, ay_ = ox + pw - 110, oy + ph + 22
        s.line(ax_, ay_, ax_ + 60, ay_, t["muted"], 1.5)
        s.add(f'<path d="M{ax_ + 66},{ay_} l-8,-4 v8 Z" fill="{t["muted"]}"/>')
        s.text(ax_ - 6, ay_ + 4, "forward", 11, t["muted"], "end")
    return s.render(f"{p.model.name} stability plan view",
                    "Support polygons and centres of gravity" + (", straight and at full articulation." if tr.articulated else "."))


# ---------------------------------------------------------------------------
# Operating modes
# ---------------------------------------------------------------------------
CONSUMERS = [("drive", "drive units"), ("pto", "PTO unit"), ("hydraulic", "hydraulic units"),
             ("steering", "steering pump"), ("aux", "12 V + idle")]


def modes_svg(p, tr, theme: str) -> str:
    from eox.calcs.bus import mode_power
    from eox.calcs.common import pack_voltages

    t = THEMES[theme]
    modes = [(name.replace("_", " "), mode_power(p, tr, m), m) for name, m in vars(p.modes).items()]
    _, V_nom, _ = pack_voltages(p.battery)
    E = V_nom * p.battery.capacity_ah * p.battery.usable_dod
    kmax = math.ceil(max(m[1]["total"] for m in modes) / 1000)
    label_w, plot_w, bar, gap = 110, 520, 22, 26
    s = Svg(label_w + plot_w + 150, 104 + len(modes) * (bar + gap) + 30, theme)
    s.text(16, 26, f"{p.model.name}: average battery power by operating mode", 16, weight=600)
    s.text(16, 44, f"one {V_nom:.1f} V {p.battery.capacity_ah:g} Ah pack, {E / 1000:.1f} kWh usable · "
           "label = total power · runtime", 11, t["ink2"])
    lx = 16
    for i, (_, label) in enumerate(CONSUMERS):
        s.add(f'<rect x="{lx}" y="58" width="12" height="12" rx="2" fill="{t["series"][i]}"/>')
        s.text(lx + 18, 68, label, 11, t["ink2"])
        lx += 34 + 6.2 * len(label)
    y0 = 96
    X = lambda w: label_w + w / 1000 / kmax * plot_w     # noqa: E731
    for k in range(kmax + 1):                             # hairline grid
        s.line(X(k * 1000), y0 - 8, X(k * 1000), y0 + len(modes) * (bar + gap) - gap + 8,
               t["grid"] if k else t["base"], 1)
        s.text(X(k * 1000), y0 + len(modes) * (bar + gap) - gap + 24, f"{k} kW", 11, t["muted"], "middle")
    for row, (name, pw, mode) in enumerate(modes):
        y = y0 + row * (bar + gap)
        s.text(label_w - 10, y + bar / 2 + 4, name, 12, t["ink"], "end")
        segs = [(i, pw[key]) for i, (key, _) in enumerate(CONSUMERS) if pw[key] > 0]
        x = 0.0
        for n, (i, w) in enumerate(segs):
            xa, xb = X(x), X(x + w)
            if n:                                         # 2 px surface gap between segments
                xa += 1
            if n < len(segs) - 1:
                xb -= 1
            if n == len(segs) - 1:                        # 4 px rounded data-end, square at the baseline
                r = min(4, (xb - xa) / 2)
                s.add(f'<path d="M{xa:.1f},{y} H{xb - r:.1f} Q{xb:.1f},{y} {xb:.1f},{y + r} V{y + bar - r} '
                      f'Q{xb:.1f},{y + bar} {xb - r:.1f},{y + bar} H{xa:.1f} Z" fill="{t["series"][i]}"/>')
            else:
                s.add(f'<rect x="{xa:.1f}" y="{y}" width="{max(xb - xa, 0.5):.1f}" height="{bar}" fill="{t["series"][i]}"/>')
            x += w
        hours = E / pw["total"]
        mark = "" if hours >= mode.runtime_target_h else f"  (target {mode.runtime_target_h:g} h)"
        s.text(X(pw["total"]) + 8, y + bar / 2 + 4, f"{pw['total'] / 1000:.1f} kW · {hours:.1f} h{mark}", 11, t["ink2"])
    return s.render(f"{p.model.name} operating modes", "Stacked bars of average battery power per operating mode, "
                    "split by consumer, with runtime on one pack.")


# ---------------------------------------------------------------------------
# Terrain course: elevation profile + per-obstacle results
# ---------------------------------------------------------------------------
STATUS = {"PASS": ("#0ca30c", "\u2713"), "WARN": ("#fab219", "!"), "FAIL": ("#d03b3b", "\u2715"), "INFO": (None, "i")}


def _wrap(text: str, width: int, lines: int = 2) -> list[str]:
    out, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1] + "\u2026"
    return out


def course_svg(p, course, results, theme: str) -> str:
    """The course profile along the centreline, then one row of obstacle
    results per configuration (status icon + label + the key number)."""
    from eox.sim.report import headline

    t = THEMES[theme]
    W, x0, label_w = 980, 40, 96
    x1 = W - 24
    k = (x1 - x0) / course.length                     # px per m
    vex = 5                                           # vertical exaggeration
    xs, zc = course.centreline()
    zmax = float(course.z.max())
    y_base = 96 + zmax * k * vex                       # ground line z = 0
    X = lambda x: x0 + x * k                           # noqa: E731
    Y = lambda z: y_base - z * k * vex                 # noqa: E731
    n = len(course.segments)
    col_w = (W - 24 - x0 - label_w) / n
    top = y_base + 0.25 * k * vex + 46
    row_h = 58
    s = Svg(W, top + 30 + row_h * len(results) + 34, theme)
    s.text(16, 26, f"{p.model.name} on the test course (MuJoCo), {course.length:.0f} m at {p.course.speed_kmh:g} km/h",
           16, weight=600)
    s.text(16, 44, f"elevation along the centreline, vertical x{vex} · rated climb {p.vehicle.max_slope_deg:g} deg; "
           "steeper ramps are scored INFO", 11, t["ink2"])

    # side-slope bands and twist humps (off the centreline, so not in the profile)
    for seg in course.segments:
        if seg.kind == "side_slope":
            s.add(f'<rect x="{X(seg.x0):.1f}" y="{Y(0) - 20:.1f}" width="{(seg.x1 - seg.x0) * k:.1f}" height="20" '
                  f'fill="{t["series"][0]}" fill-opacity="0.14"/>')
            s.text(X((seg.x0 + seg.x1) / 2), Y(0) - 6, f"{seg.spec.slope_deg:g} deg across", 10, t["ink2"], "middle")
        if seg.kind == "twist":
            r0 = seg.spec.length / 2
            for i in range(seg.spec.count):
                cx = X(seg.x0 + r0 + i * seg.spec.pitch)
                s.add(f'<circle cx="{cx:.1f}" cy="{Y(0) - 6:.1f}" r="3" fill="{t["series"][0]}"/>')
    pts = " ".join(f"{X(x):.1f},{Y(z):.1f}" for x, z in zip(xs[::2], zc[::2]))
    s.add(f'<polygon points="{X(0):.1f},{Y(-0.3):.1f} {pts} {X(course.length):.1f},{Y(-0.3):.1f}" '
          f'fill="{t["grid"]}" stroke="none"/>')
    s.add(f'<polyline points="{pts}" fill="none" stroke="{t["ink2"]}" stroke-width="2" stroke-linejoin="round"/>')
    for i, seg in enumerate(course.segments, 1):
        cx = X((seg.x0 + seg.x1) / 2)
        zt = float(zc[(xs >= seg.x0) & (xs <= seg.x1)].max())
        cy = Y(max(zt, 0)) - 30
        s.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{t["surface"]}" stroke="{t["ink2"]}" stroke-width="1"/>')
        s.text(cx, cy + 4, i, 10, t["ink"], "middle", weight=600)
    s.text(X(0), Y(-0.3) + 16, "start", 10, t["muted"])
    s.text(X(course.length), Y(-0.3) + 16, f"{course.length:.0f} m", 10, t["muted"], "end")

    # results grid
    gx = x0 + label_w
    for i, seg in enumerate(course.segments, 1):
        s.text(gx + (i - 0.5) * col_w, top + 14, f"{i} {seg.name}", 11, t["ink"], "middle", weight=600)
    s.line(x0, top + 24, x1, top + 24, t["base"], 1)
    for rnum, r in enumerate(results):
        y = top + 30 + rnum * row_h
        s.text(x0, y + 20, r.config, 12, t["ink"], weight=600)
        if rnum:
            s.line(x0, y - 3, x1, y - 3, t["grid"], 1)
        for i, o in enumerate(r.obstacles):
            cx = gx + i * col_w + 10
            colour, glyph = STATUS[o.status]
            fill = colour or t["muted"]
            s.add(f'<circle cx="{cx + 7:.1f}" cy="{y + 15:.1f}" r="7" fill="{fill}"/>')
            s.text(cx + 7, y + 19, glyph, 10, "#ffffff" if o.status != "WARN" else "#0b0b0b", "middle", weight=700)
            s.text(cx + 19, y + 19, o.status, 11, t["ink"], weight=600)
            for j, ln in enumerate(_wrap(headline(o), int(col_w / 5.6))):
                s.text(cx, y + 35 + 12 * j, ln, 10, t["ink2"])
    return s.render(f"{p.model.name} terrain course results",
                    "Course elevation profile with numbered obstacles, and per-configuration results: " +
                    "; ".join(f"{r.config}: " + ", ".join(f"{o.name} {o.status}" for o in r.obstacles) for r in results))


def write_course(p, course, results, out_dir) -> list[str]:
    model = p.model.name.split()[-1].lower()
    written = []
    for theme in THEMES:
        f = out_dir / f"{model}-course-{theme}.svg"
        f.write_text(course_svg(p, course, results, theme))
        written.append(str(f))
    return written


def write_all(p, tr, out_dir) -> list[str]:
    """Write every figure in both themes; returns the paths written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "flats").mkdir(exist_ok=True)
    model = p.model.name.split()[-1].lower()
    written = []
    for theme in THEMES:
        for part in tr.box.parts:
            qty = sum(1 for pl in tr.box.placed if pl.part is part)
            f = out_dir / "flats" / f"{part.part_no}-{theme}.svg"
            f.write_text(flat_svg(part, theme, qty))
            written.append(f)
        for name, fn in (("stability", lambda th: stability_svg(tr, th)), ("modes", lambda th: modes_svg(p, tr, th))):
            f = out_dir / f"{model}-{name}-{theme}.svg"
            f.write_text(fn(theme))
            written.append(f)
    return [str(w) for w in written]
