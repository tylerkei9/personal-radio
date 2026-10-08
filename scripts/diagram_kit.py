"""Tiny SVG drawing kit (standard library only) used by make_diagrams.py.

Rules enforced here: ASCII text only (no emoji, no special glyphs, no em dashes), every figure has a title and
description for screen readers, and each figure carries its own light card background so it reads on any theme.
"""
import math
from xml.sax.saxutils import escape

BG, BORDER = "#fcfcfb", "#d9d8d2"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a897f", "#e6e5df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
BLUE_T, ORANGE_T, AQUA_T, GREY_T = "#dbe8f8", "#fbe3d9", "#d7f1e6", "#efeee9"
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


class Fig:
    def __init__(self, w: int, h: int, title: str, desc: str):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.parts: list[str] = []

    def add(self, s: str):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=None, rx=0, sw=1, dash=None, opacity=None):
        a = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if opacity is not None:
            a += f' opacity="{opacity}"'
        self.add(a + "/>")

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight="normal", italic=False):
        st = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}"{st}>{escape(s)}</text>')

    def lines(self, x, y, rows, size=13, lh=None, **kw):
        lh = lh or size * 1.35
        for i, r in enumerate(rows):
            self.text(x, y + i * lh, r, size=size, **kw)

    def line(self, x1, y1, x2, y2, stroke=INK2, sw=1.5, dash=None, cap="butt"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{sw}" stroke-linecap="{cap}"{d}/>')

    def poly(self, pts, fill="none", stroke=None, sw=1.5):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ""
        self.add(f'<polygon points="{p}" fill="{fill}"{s}/>')

    def polyline(self, pts, stroke=INK, sw=2):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')

    def circle(self, x, y, r, fill="none", stroke=None, sw=1.5):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"{s}/>')

    def arrow(self, x1, y1, x2, y2, color=INK2, sw=1.8, head=8, dash=None):
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
        self.line(x1, y1, bx, by, color, sw, dash)
        px, py = -math.sin(ang), math.cos(ang)
        self.poly([(x2, y2), (bx + px * head * 0.5, by + py * head * 0.5), (bx - px * head * 0.5, by - py * head * 0.5)],
                  fill=color)

    def tick_mark(self, cx, cy, s=7, color=BLUE, sw=2.4):          # drawn check mark (no glyph)
        self.polyline([(cx - s, cy), (cx - s * 0.3, cy + s * 0.7), (cx + s, cy - s * 0.7)], color, sw)

    def cross_mark(self, cx, cy, s=6, color=ORANGE, sw=2.4):        # drawn cross (no glyph)
        self.line(cx - s, cy - s, cx + s, cy + s, color, sw, cap="round")
        self.line(cx - s, cy + s, cx + s, cy - s, color, sw, cap="round")

    def box(self, x, y, w, h, title=None, sub=None, fill=GREY_T, stroke=BORDER, tsize=14, ssize=12, tcolor=INK):
        self.rect(x, y, w, h, fill, stroke, rx=8)
        cy = y + h / 2
        if title and sub:
            self.text(x + w / 2, cy - 2, title, tsize, tcolor, "middle", "600")
            self.text(x + w / 2, cy + 16, sub, ssize, INK2, "middle")
        elif title:
            self.text(x + w / 2, cy + 5, title, tsize, tcolor, "middle", "600")

    def axis_y(self, x, y0, y1, vals, fmt, size=11):
        for v, yy in vals:
            self.line(x, yy, x + 6, yy, MUTED, 1)
            self.text(x - 6, yy + 4, fmt(v), size, INK2, "end")

    def svg(self) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-label="{escape(self.title)}. {escape(self.desc)}" '
                f'font-family="{FONT}">')
        body = [f"<title>{escape(self.title)}</title>", f"<desc>{escape(self.desc)}</desc>",
                f'<rect x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>']
        out = head + "".join(body) + "".join(self.parts) + "</svg>\n"
        bad = sorted({c for c in out if ord(c) > 126})
        assert not bad, f"non-ASCII characters in figure '{self.title}': {bad}"
        return out


def heading(f: Fig, title: str, sub: str | None = None):
    f.text(24, 34, title, 17, INK, weight="700")
    if sub:
        f.text(24, 54, sub, 12.5, INK2)
