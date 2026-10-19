"""Single-bend-per-edge sheet metal parts: 3D solid, flat pattern, SCS checks.

A FlangedPanel is a rectangular base with an optional 90 deg flange on each of
its four edges. That covers trays, covers, U-channels, angles and flat plates,
which is everything the power box needs.

Local frame: base outer face (OML) on z=0, material toward +z, flanges bend
toward +z. u is x, v is y. Edges are named "+u", "-u", "+v", "-v".

Corners where two flanges meet: the v-flanges (along x) run to the outer
corner, the u-flanges stop `corner_gap` short of the v-flange's inside face.
Where a flange runs past the end of its bend, a square relief keeps the
extension clear of the bend zone (SCS relief depth, measured from the bend line).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import reduce

IN = 25.4
EDGES = ("+v", "-v", "+u", "-u")
# per edge: rotation about z that takes the canonical (+v) build onto it, and
# the sign mapping the global along-edge coordinate to canonical x
_ROT = {"+v": (0, 1), "-v": (180, -1), "-u": (90, 1), "+u": (-90, -1)}


@dataclass(frozen=True)
class Gauge:
    material: str
    t: float            # thickness, mm
    r: float            # inside bend radius, mm
    k: float            # k-factor
    die: float          # V-die width, mm
    min_flange: float   # minimum formed flange (OML), mm
    relief: float       # relief depth from the bend line, mm
    max_bend_len: float
    density: float      # kg/m^3
    yield_mpa: float
    E_mpa: float
    k_w_mk: float = 138.0   # thermal conductivity

    @property
    def ossb(self) -> float:
        """Outside setback for a 90 deg bend."""
        return self.r + self.t

    @property
    def ba(self) -> float:
        """Bend allowance (neutral-axis arc length) for 90 deg."""
        return math.pi / 2 * (self.r + self.k * self.t)

    @property
    def bd(self) -> float:
        """Bend deduction for 90 deg: flat = sum of OML legs - bd per bend."""
        return 2 * self.ossb - self.ba

    @property
    def min_feature_to_bend(self) -> float:
        """SCS: cut features at least half the die width from the bend line."""
        return self.die / 2


@dataclass
class Hole:
    face: str      # "base" or an edge name
    s: float       # base: x.  flange: global coordinate along the edge (x on +-v, y on +-u)
    h: float       # base: y.  flange: height above the base OML
    d: float
    label: str = ""
    length: float = 0.0   # > 0 makes it a slot: centre-to-centre length, running along s

    @property
    def area(self) -> float:
        return math.pi * self.d ** 2 / 4 + self.d * self.length


def _cutter(d: float, length: float, depth: float):
    """Through-cutter on the XY plane, axis Z; a slot runs along X."""
    from build123d import Box, Cylinder, Pos

    c = Cylinder(d / 2, depth)
    if length:
        c = (Pos(-length / 2, 0, 0) * c + Pos(length / 2, 0, 0) * Cylinder(d / 2, depth)
             + Box(length, d, depth))
    return c


@dataclass
class FlangedPanel:
    part_no: str
    name: str
    A: float                       # OML along u (x)
    B: float                       # OML along v (y)
    g: Gauge
    flanges: dict[str, float] = field(default_factory=dict)  # edge -> OML height
    holes: list[Hole] = field(default_factory=list)
    qty: int = 1
    corner_gap: float = 0.5
    note: str = ""

    # ----- layout ---------------------------------------------------------
    def half(self, e: str) -> float:
        return self.A / 2 if e[1] == "u" else self.B / 2

    def _sb(self, e: str) -> float:
        return self.g.ossb if e in self.flanges else 0.0

    def base_rect(self) -> tuple[float, float, float, float]:
        """Flat (unbent) region of the base: x0, y0, x1, y1."""
        return (-self.A / 2 + self._sb("-u"), -self.B / 2 + self._sb("-v"),
                self.A / 2 - self._sb("+u"), self.B / 2 - self._sb("+v"))

    def _neighbours(self, e: str) -> tuple[str, str]:
        return ("-u", "+u") if e[1] == "v" else ("-v", "+v")

    def bend_span(self, e: str) -> tuple[float, float]:
        x0, y0, x1, y1 = self.base_rect()
        return (x0, x1) if e[1] == "v" else (y0, y1)

    def flange_span(self, e: str) -> tuple[float, float]:
        lo, hi = self.bend_span(e)
        n_lo, n_hi = self._neighbours(e)
        if e[1] == "v":
            reach = self.A / 2                                   # run to the outer corner
        else:
            reach = self.B / 2 - self.g.t - self.corner_gap      # stop at the v-flange
        if n_lo in self.flanges:
            lo = -reach
        if n_hi in self.flanges:
            hi = reach
        return lo, hi

    def _out(self, e: str) -> tuple[float, float, float, float]:
        """Flat distances from the centre, outward across edge e:
        bend start, bend end, relief line (extensions start here), flange top."""
        g, H = self.g, self.flanges[e]
        b0 = self.half(e) - g.ossb
        b1 = b0 + g.ba
        rel = max(b1, b0 + g.ba / 2 + g.relief)
        top = self.half(e) + H - g.bd
        return b0, b1, rel, top

    @staticmethod
    def _xy(e: str, along: float, out: float) -> tuple[float, float]:
        return {"+v": (along, out), "-v": (along, -out),
                "+u": (out, along), "-u": (-out, along)}[e]

    # ----- flat pattern ---------------------------------------------------
    def flat_rects(self) -> list[tuple[float, float, float, float]]:
        rects = [self.base_rect()]
        for e in self.flanges:
            b0, b1, rel, top = self._out(e)
            lo, hi = self.bend_span(e)
            flo, fhi = self.flange_span(e)
            pieces = [(lo, hi, b0, top)]
            if flo < lo:
                pieces.append((flo, lo, rel, top))
            if fhi > hi:
                pieces.append((hi, fhi, rel, top))
            for a0, a1, o0, o1 in pieces:
                (xa, ya), (xb, yb) = self._xy(e, a0, o0), self._xy(e, a1, o1)
                rects.append((min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)))
        return rects

    def flat_point(self, hole: Hole) -> tuple[float, float]:
        if hole.face == "base":
            return hole.s, hole.h
        return self._xy(hole.face, hole.s, self.half(hole.face) + hole.h - self.g.bd)

    def _along_flat_x(self, hole: Hole) -> bool:
        """True when the hole's s axis runs along flat x (slot orientation)."""
        return hole.face == "base" or hole.face[1] == "v"

    def _flat_centres(self, hole: Hole) -> list[tuple[float, float]]:
        """End-circle centres of a slot (one centre for a round hole)."""
        x, y = self.flat_point(hole)
        if not hole.length:
            return [(x, y)]
        dx, dy = ((hole.length / 2, 0) if self._along_flat_x(hole) else (0, hole.length / 2))
        return [(x - dx, y - dy), (x + dx, y + dy)]

    def bend_lines(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        lines = []
        for e in self.flanges:
            b0, b1, _, _ = self._out(e)
            mid = (b0 + b1) / 2
            lo, hi = self.bend_span(e)
            lines.append((self._xy(e, lo, mid), self._xy(e, hi, mid)))
        return lines

    def flat_bbox(self) -> tuple[float, float]:
        rs = self.flat_rects()
        return (max(r[2] for r in rs) - min(r[0] for r in rs),
                max(r[3] for r in rs) - min(r[1] for r in rs))

    def flat_area_mm2(self) -> float:
        # rects never overlap by construction (they only share edges)
        area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in self.flat_rects())
        return area - sum(h.area for h in self.holes)

    def mass_kg(self) -> float:
        return self.flat_area_mm2() * self.g.t * self.g.density * 1e-9

    # ----- 3D -------------------------------------------------------------
    def solid(self):
        from build123d import Align, Box, Cylinder, Pos, Rot

        g = self.g
        t, r, sb = g.t, g.r, g.ossb

        def box(x0, x1, y0, y1, z0, z1):
            return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)

        x0, y0, x1, y1 = self.base_rect()
        parts = [box(x0, x1, y0, y1, 0, t)]
        cutters = [Pos(h.s, h.h, t / 2) * _cutter(h.d, h.length, t * 4)
                   for h in self.holes if h.face == "base"]

        for e, H in self.flanges.items():
            rot, sign = _ROT[e]
            half = self.half(e)
            lo, hi = sorted(sign * v for v in self.bend_span(e))
            flo, fhi = sorted(sign * v for v in self.flange_span(e))
            _, b1, rel, _ = self._out(e)
            z_rel = sb + (rel - b1)
            yc, zc = half - sb, sb

            L = hi - lo
            ring = Cylinder(r + t, L, rotation=(0, 90, 0)) - Cylinder(r, L, rotation=(0, 90, 0))
            quad = Box(L, r + t, r + t, align=(Align.CENTER, Align.MIN, Align.MAX))
            local = [Pos((lo + hi) / 2, yc, zc) * (ring & quad),
                     box(lo, hi, half - t, half, sb, H)]
            if flo < lo:
                local.append(box(flo, lo, half - t, half, z_rel, H))
            if fhi > hi:
                local.append(box(hi, fhi, half - t, half, z_rel, H))
            parts += [Rot(0, 0, rot) * p for p in local]
            cutters += [Rot(0, 0, rot) * Pos(sign * h.s, half - t / 2, h.h) * Rot(90, 0, 0)
                        * _cutter(h.d, h.length, t * 4)
                        for h in self.holes if h.face == e]

        body = reduce(lambda a, b: a + b, parts)
        if cutters:
            body = body - reduce(lambda a, b: a + b, cutters)
        return body

    def flat_face(self):
        from build123d import Circle, Pos, Rectangle, Rot, SlotCenterToCenter

        face = reduce(lambda a, b: a + b, [
            Pos((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) * Rectangle(r[2] - r[0], r[3] - r[1])
            for r in self.flat_rects()])
        for h in self.holes:
            if h.length:
                cut = SlotCenterToCenter(h.length, h.d)
                if not self._along_flat_x(h):
                    cut = Rot(0, 0, 90) * cut
            else:
                cut = Circle(h.d / 2)
            face = face - Pos(*self.flat_point(h)) * cut
        return face

    def export(self, out_dir) -> dict[str, str]:
        """Write <part>.step (formed, for SCS) and <part>_flat.dxf (reference)."""
        from build123d import ExportDXF, Line, Unit, export_step

        out_dir.mkdir(parents=True, exist_ok=True)
        step = out_dir / f"{self.part_no}.step"
        export_step(self.solid(), str(step))
        dxf = out_dir / f"{self.part_no}_flat.dxf"
        ex = ExportDXF(unit=Unit.MM)
        ex.add_layer("CUT")
        ex.add_layer("BEND")
        ex.add_shape(self.flat_face(), layer="CUT")
        for a, b in self.bend_lines():
            ex.add_shape(Line(a, b), layer="BEND")
        ex.write(str(dxf))
        return {"step": str(step), "dxf": str(dxf)}

    # ----- SCS manufacturability ------------------------------------------
    def scs_checks(self, scs) -> list:
        from eox.checks import Check

        g, grp, out = self.g, f"SCS {self.part_no}", []
        fx, fy = self.flat_bbox()
        lim = [v * IN for v in (scs.bend_flat_max_in if self.flanges else scs.laser_sheet_max_in)]
        usage = max(max(fx, fy) / max(lim), min(fx, fy) / min(lim))  # <= 1 means it fits
        out.append(Check(grp, f"flat {fx:.0f} x {fy:.0f} mm fits {lim[0]/IN:.0f}x{lim[1]/IN:.0f} in",
                         round(usage, 3), "of max", 1.0, "<=", 0.03))
        for e, H in self.flanges.items():
            out.append(Check(grp, f"flange {e} >= min flange", H, "mm", round(g.min_flange, 2), ">="))
            lo, hi = self.bend_span(e)
            out.append(Check(grp, f"bend {e} length", hi - lo, "mm", round(g.max_bend_len, 1), "<="))
        for a, b in (("+u", "-u"), ("+v", "-v")):
            if a in self.flanges and b in self.flanges:
                base = (self.A if a[1] == "u" else self.B) - 2 * g.t
                need = scs.u_channel_base_to_flange * max(self.flanges[a], self.flanges[b])
                out.append(Check(grp, f"U-channel base ({a[1]}) >= {scs.u_channel_base_to_flange:g}x flange",
                                 round(base, 1), "mm", round(need, 1), ">="))
        if self.holes:
            worst = min(self._hole_to_bend(h) for h in self.holes)
            if worst < math.inf:
                out.append(Check(grp, "hole edge to bend line", round(worst, 2), "mm",
                                 round(g.min_feature_to_bend, 2), ">=", note="SCS: >= half die width"))
            out.append(Check(grp, "smallest hole >= t", min(h.d for h in self.holes), "mm", round(g.t, 2), ">="))
            out.append(Check(grp, "hole edge to part edge >= 2t", round(min(self._hole_to_edge(h) for h in self.holes), 2),
                             "mm", round(2 * g.t, 2), ">="))
            if len(self.holes) > 1:
                out.append(Check(grp, "web between holes >= t", round(self._min_web(), 2), "mm", round(g.t, 2), ">="))
        return out

    def _min_web(self) -> float:
        best = math.inf
        cs = [(h, self._flat_centres(h)) for h in self.holes]
        for i, (hi, ci) in enumerate(cs):
            for hj, cj in cs[i + 1:]:
                gap = min(math.hypot(a[0] - b[0], a[1] - b[1]) for a in ci for b in cj) - (hi.d + hj.d) / 2
                best = min(best, gap)
        return best

    def _hole_to_bend(self, h: Hole) -> float:
        return min(self._circle_to_bend(px, py, h.d) for px, py in self._flat_centres(h))

    def _circle_to_bend(self, px: float, py: float, d: float) -> float:
        best = math.inf
        for (ax, ay), (bx, by) in self.bend_lines():
            dx, dy = bx - ax, by - ay
            u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(px - ax - u * dx, py - ay - u * dy) - d / 2)
        return best

    def _hole_to_edge(self, h: Hole) -> float:
        """Distance from hole edge to the nearest outline edge of the flat."""
        return min(self._circle_to_edge(px, py) for px, py in self._flat_centres(h)) - h.d / 2

    def _circle_to_edge(self, px: float, py: float) -> float:
        best = math.inf
        for x0, y0, x1, y1 in self.flat_rects():
            if x0 <= px <= x1 and y0 <= py <= y1:
                # only edges of this rect that are on the outline count
                for edge_d, ex, ey in ((px - x0, x0 - 1e-3, py), (x1 - px, x1 + 1e-3, py),
                                       (py - y0, px, y0 - 1e-3), (y1 - py, px, y1 + 1e-3)):
                    if not self._inside(ex, ey):
                        best = min(best, edge_d)
        return best

    def _inside(self, x: float, y: float) -> bool:
        return any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in self.flat_rects())
