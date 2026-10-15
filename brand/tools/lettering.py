"""The two letterings for round 3. Both come from Hanken Grotesk, so every
lowercase letter, digit, and hyphen exists and any project name can be set.

hanken: Hanken Grotesk 600, re-cut.
  - b d f h k l ascend to 1.6 x-heights.
  - t has a flat top, level with the top of the tittle.
  - The tittles of i and j are squares one stem wide.
  - Spacing is set by hand. GPOS kerning is not used.

round: a constant-stroke lettering with round ends, drawn from the Thin
  master's skeleton. The Thin outline is eroded to a hairline core, then
  grown back to the stroke width with round joins. Ascenders get the same
  1.6 x-height stretch as the hanken lettering, so the two set on one grid.

Both return path data in units where the x-height is XH_OUT (100).
"""

import math
import os

import pathops
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

_PATH = os.path.join(os.environ["BRAND_FONT_DIR"], "variable", "HankenGrotesk[wght].ttf")
_FONTS = {}

XH = 493.0  # font units
ASC = 697.0
ASC_NEW = XH * 1.6
STEM600 = 110.8
XH_OUT = 100.0
ASCENDERS = "bdfhkl"


def _font(w):
    if w not in _FONTS:
        tt = instantiateVariableFont(TTFont(_PATH), {"wght": w})
        _FONTS[w] = (tt.getGlyphSet(), tt.getBestCmap())
    return _FONTS[w]


def _rec(w, ch):
    gs, cmap = _font(w)
    g = gs[cmap[ord(ch)]]
    rp = DecomposingRecordingPen(gs)
    g.draw(rp)
    return rp.value, g.width


def _contours(rec):
    cur = []
    for op, pts in rec:
        cur.append((op, pts))
        if op in ("closePath", "endPath"):
            yield cur
            cur = []


def _stretch(ch, rec, t_top):
    """Raise ascenders to ASC_NEW and flatten the top of t at t_top."""
    out = []
    for op, pts in rec:
        npts = []
        for x, y in pts:
            if ch == "t" and y > 520:
                y = t_top
            elif ch in ASCENDERS and y > 520:
                y += ASC_NEW - ASC
            npts.append((x, y))
        out.append((op, tuple(npts)))
    return out


def _ntos(prec):
    def f(v):
        s = f"{v:.{prec}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s

    return f


def _svg(drawable, k, dx, dy, prec, max_err):
    pen = SVGPathPen(None, ntos=_ntos(prec))
    tp = TransformPen(pen, (k, 0, 0, -k, dx, dy))
    drawable(Qu2CuPen(tp, max_err=max_err, all_cubic=True))
    return pen.getCommands()


def _bounds_x(path):
    xmin, _, xmax, _ = path.bounds
    return xmin, xmax


def _to_path(rec):
    p = pathops.Path()
    pen = p.getPen()
    for op, pts in rec:
        getattr(pen, op)(*pts)
    return p


# --- hanken ----------------------------------------------------------------

TITTLE = STEM600  # square tittle, one stem wide
TITTLE_BOTTOM = 586.0
T_TOP = TITTLE_BOTTOM + TITTLE


def hanken_glyph(ch):
    """pathops.Path in font units, and advance width."""
    rec, adv = _rec(600, ch)
    body = []
    dot = None
    for c in _contours(rec):
        ys = [y for _, pts in c for _, y in pts]
        xs = [x for _, pts in c for x, _ in pts]
        if ch in "ij" and min(ys) > XH:
            cx = (min(xs) + max(xs)) / 2
            dot = cx
            continue
        body += c
    p = _to_path(_stretch(ch, body, T_TOP))
    if dot is not None:
        h = TITTLE / 2
        sq = pathops.Path()
        sq.moveTo(dot - h, TITTLE_BOTTOM)
        sq.lineTo(dot - h, TITTLE_BOTTOM + TITTLE)
        sq.lineTo(dot + h, TITTLE_BOTTOM + TITTLE)
        sq.lineTo(dot + h, TITTLE_BOTTOM)
        sq.close()
        p = pathops.op(p, sq, pathops.PathOp.UNION)
    else:
        p.simplify()
    return p, adv


# --- round -----------------------------------------------------------------

CAP, JOIN = pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN
ERODE = 6.0  # the Thin stem is 20, its horizontals about 14
CONIC_TOL = 0.02
CORE = 3.0  # half the width the core keeps, on average


def _dilate(p, r):
    q = pathops.Path(p)
    q.stroke(2 * r, CAP, JOIN, 4)
    q.convertConicsToQuads(CONIC_TOL)
    return pathops.op(p, q, pathops.PathOp.UNION)


def _erode(p, r):
    xmin, ymin, xmax, ymax = p.bounds
    m = 4 * r + 20
    box = pathops.Path()
    box.moveTo(xmin - m, ymin - m)
    box.lineTo(xmax + m, ymin - m)
    box.lineTo(xmax + m, ymax + m)
    box.lineTo(xmin - m, ymax + m)
    box.close()
    c = pathops.op(box, p, pathops.PathOp.DIFFERENCE)
    return pathops.op(box, _dilate(c, r), pathops.PathOp.DIFFERENCE)


def _circle(cx, cy, r):
    k = 0.5522847498 * r
    p = pathops.Path()
    p.moveTo(cx + r, cy)
    p.cubicTo(cx + r, cy + k, cx + k, cy + r, cx, cy + r)
    p.cubicTo(cx - k, cy + r, cx - r, cy + k, cx - r, cy)
    p.cubicTo(cx - r, cy - k, cx - k, cy - r, cx, cy - r)
    p.cubicTo(cx + k, cy - r, cx + r, cy - k, cx + r, cy)
    p.close()
    return p


def round_glyph(ch, S):
    """pathops.Path in font units for stroke width S, and advance width.

    The ink of a flat stroke end moves by r - ERODE, where r is the growth
    radius. The x-height zone runs from the bottom of x to the top of x, and
    the ascender, the t, and the tittle sit at the same proportions of that
    zone as in the hanken lettering."""
    r = S / 2 - CORE
    grow = r - ERODE
    zb, zt = -grow, XH + grow
    zh = zt - zb
    asc_ink = zb + 1.6 * zh
    dot_c = zb + (TITTLE_BOTTOM + TITTLE / 2) / XH * zh
    dot_r = S / 2 * 1.06
    t_ink = dot_c + dot_r
    rec, adv = _rec(100, ch)
    body, dots = [], []
    for c in _contours(rec):
        ys = [y for _, pts in c for _, y in pts]
        xs = [x for _, pts in c for x, _ in pts]
        if ch in "ij" and min(ys) > XH:
            dots.append((min(xs) + max(xs)) / 2)
            continue
        body += c
    rec2 = []
    for op, pts in body:
        npts = []
        for x, y in pts:
            if ch == "t" and y > 520:
                y = t_ink - grow
            elif ch in ASCENDERS and y > 520:
                y += asc_ink - (ASC + grow)
            npts.append((x, y))
        rec2.append((op, tuple(npts)))
    p = _to_path(rec2)
    p.simplify()
    p = _erode(p, ERODE)
    p = _dilate(p, r)
    for cx in dots:
        p = pathops.op(p, _circle(cx, dot_c, dot_r), pathops.PathOp.UNION)
    return p, adv + 2 * grow


def round_zone(S):
    grow = S / 2 - CORE - ERODE
    return -grow, XH + grow


# --- setting ---------------------------------------------------------------


class Lettering:
    def __init__(self, name, glyph, zone, track, kern, prec, max_err):
        self.name, self._glyph, self.track, self.kern, self.prec = name, glyph, track, kern, prec
        self.max_err = max_err  # cubic refit tolerance, font units
        self.zone = zone  # (bottom, top) of the x-height zone, font units
        self._cache = {}

    def glyph(self, ch):
        if ch not in self._cache:
            self._cache[ch] = self._glyph(ch)
        return self._cache[ch]

    def line(self, text, x0, base, xh=XH_OUT):
        """Set text with the first glyph's ink at x0 and the baseline at base.
        Returns (path data, right edge of the ink)."""
        zb, zt = self.zone
        k = xh / (zt - zb)
        base = base + zb * k
        p0, _ = self.glyph(text[0])
        x = x0 - _bounds_x(p0)[0] * k
        parts = []
        right = x0
        prev = None
        for ch in text:
            if prev is not None:
                x += (self.track + self.kern.get(prev + ch, 0)) * k
            p, adv = self.glyph(ch)
            parts.append(_svg(p.draw, k, x, base, self.prec, self.max_err))
            right = x + _bounds_x(p)[1] * k
            x += adv * k
            prev = ch
        return "".join(parts), right


HANKEN_KERN = {
    "ba": 4, "sk": 4, "ki": 6, "ng": -2, "sp": 4, "po": -2, "ot": -8,
    "st": -2, "dx": -6, "ls": 2, "co": -4, "pr": -2, "re": -6, "es": -2,
    "be": -2, "nc": -2, "ma": -2, "rk": -8, "te": -8, "ti": 4, "im": 4,
    "ty": -10, "yp": -4, "js": 0, "so": -2, "on": 0, "ht": 0, "tp": 0,
    "lo": -2, "og": -2, "cl": 0, "li": 4, "rr": -4, "ro": -6, "ap": 0,
    "ce": -4, "ec": -4, "fm": -6, "ex": -6, "xp": -6, "gu": 0, "uu": 0,
    "ui": 4, "id": 4, "ar": -2, "rg": -4, "gs": 0, "ha": 0, "as": 0,
    "sh": 2, "zo": -4, "ze": -4, "mt": -4, "tl": 0, "ve": -8, "ev": -8,
    "fs": -4, "ft": -10, "tf": -10, "ry": -10, "yr": -10, "ny": -6,
    "ys": -6,
}

ROUND_KERN = {
    "ba": 2, "sk": 4, "ki": 4, "ot": -10, "dx": -6, "co": -4, "re": -8,
    "rk": -10, "te": -10, "ty": -14, "ro": -8, "ce": -4, "ec": -4,
    "fm": -8, "ex": -8, "xp": -8, "ve": -10, "ev": -10, "ft": -14,
    "tf": -14, "ry": -14, "yr": -14, "ny": -8, "ys": -8, "zo": -4,
    "st": -4, "ts": -4, "po": -2, "rr": -6, "mt": -4, "fs": -6,
}

ROUND_S = 100.0  # stroke, font units: 17.4% of the ink x-height

HANKEN = Lettering("hanken", hanken_glyph, (0.0, XH), -14, HANKEN_KERN, 0, 0.6)
ROUND = Lettering("round", lambda ch: round_glyph(ch, ROUND_S), round_zone(ROUND_S), -6, ROUND_KERN, 1, 2.0)
