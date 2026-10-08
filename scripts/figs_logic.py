"""Figures 06-09: the two-way check, the three corrections, the playlist slots, selection probabilities."""
import math
import os
import random
import sys
from diagram_kit import *

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Plot:
    """Axes with linear or log scales, drawn from data values."""
    def __init__(self, f, x, y, w, h, xr, yr, xlog=False, ylog=False):
        self.f, self.x, self.y, self.w, self.h, self.xr, self.yr, self.xlog, self.ylog = f, x, y, w, h, xr, yr, xlog, ylog

    def px(self, v):
        a, b = self.xr
        t = (math.log(v / a) / math.log(b / a)) if self.xlog else (v - a) / (b - a)
        return self.x + t * self.w

    def py(self, v):
        a, b = self.yr
        t = (math.log(v / a) / math.log(b / a)) if self.ylog else (v - a) / (b - a)
        return self.y + self.h - t * self.h

    def frame(self, xticks, yticks, xfmt=str, yfmt=str, xlabel="", ylabel=""):
        f = self.f
        for v in yticks:
            f.line(self.x, self.py(v), self.x + self.w, self.py(v), GRID, 1)
            f.text(self.x - 6, self.py(v) + 4, yfmt(v), 10.5, INK2, "end")
        for v in xticks:
            f.line(self.px(v), self.y + self.h, self.px(v), self.y + self.h + 5, MUTED, 1)
            f.text(self.px(v), self.y + self.h + 18, xfmt(v), 10.5, INK2, "middle")
        f.line(self.x, self.y + self.h, self.x + self.w, self.y + self.h, MUTED, 1.2)
        f.line(self.x, self.y, self.x, self.y + self.h, MUTED, 1.2)
        if xlabel:
            f.text(self.x + self.w / 2, self.y + self.h + 36, xlabel, 11.5, INK2, "middle")
        if ylabel:
            f.text(self.x, self.y - 10, ylabel, 11.5, INK2)

    def line(self, pts, color, sw=2.4):
        self.f.polyline([(self.px(a), self.py(b)) for a, b in pts], color, sw)


def fig06():
    f = Fig(960, 470, "The two-way check removes hub songs",
            "Left: a hub song appears in X's list, but X is missing from the hub's own list, so it scores low. Right: a good fit appears in X's list and X appears in its list, so it scores high.")
    heading(f, "The two-way check removes hub songs", "A candidate only counts as similar if it also points back at your song.")

    def lst(x, y, title, rows, mark, mark_color, extra=None):
        f.text(x, y - 12, title, 12, INK, weight="600")
        for i, r in enumerate(rows):
            hit = i == mark
            f.rect(x, y + i * 28, 180, 24, mark_color if hit else "#ffffff", BORDER if not hit else "#ffffff", rx=4)
            f.text(x + 10, y + i * 28 + 16.5, f"#{i + 1}  {r}", 12, "#ffffff" if hit else INK2, weight="700" if hit else "normal")
        if extra:
            f.text(x + 90, y + len(rows) * 28 + 12, extra, 11, MUTED, "middle")

    # left: hub
    f.text(24, 92, "A hub song (listed by everyone)", 14, INK, weight="700")
    lst(30, 130, "X's neighbours", ["Song P", "Hub H", "Song Q", "Song R", "Song S"], 1, ORANGE, "...50 entries")
    lst(250, 130, "Hub H's own neighbours", ["Song G1", "Song G2", "Song G3", "Song G4", "Song G5"], -1, ORANGE, "...50 entries, X is not in them")
    f.arrow(214, 168, 246, 168, INK2)
    f.text(230, 154, "points", 10, INK2, "middle"); 
    f.cross_mark(230, 190, 7, ORANGE, 2.6)
    f.text(230, 214, "no", 10.5, INK2, "middle")
    f.rect(30, 340, 400, 84, ORANGE_T, ORANGE, rx=8)
    f.text(44, 364, "Forward score: 0.98 (rank 2 of 50)", 12.5, INK)
    f.text(44, 384, "Backward score: 0.10 (X not in the hub's list)", 12.5, INK)
    f.text(44, 408, "Combined = sqrt(0.98 x 0.10) = 0.31  (low)", 13, INK, weight="700")
    # right: good fit
    f.text(504, 92, "A good fit", 14, INK, weight="700")
    lst(510, 130, "X's neighbours", ["Song P", "Song R", "Fit F", "Song S", "Song T"], 2, AQUA, "...50 entries")
    lst(730, 130, "F's own neighbours", ["Song U", "Song V", "X", "Song W", "Song Y"], 2, BLUE, "...50 entries, X is #3")
    f.arrow(694, 168, 726, 168, INK2)
    f.text(710, 154, "points", 10, INK2, "middle")
    f.tick_mark(710, 190, 7, BLUE, 2.6)
    f.text(710, 214, "yes", 10.5, INK2, "middle")
    f.rect(510, 340, 420, 84, AQUA_T, AQUA, rx=8)
    f.text(524, 364, "Forward score: 0.96 (rank 3 of 50)", 12.5, INK)
    f.text(524, 384, "Backward score: 0.96 (X is #3 in F's list)", 12.5, INK)
    f.text(524, 408, "Combined = sqrt(0.96 x 0.96) = 0.96  (high)", 13, INK, weight="700")
    f.line(480, 80, 480, 440, BORDER, 1, dash="4 4")
    return f


def fig07():
    f = Fig(960, 420, "Three corrections applied to every candidate",
            "Three small charts: the two-way factor by rank, breadth damping that grows with the square root of the number of seeds, and the popularity multiplier on a log scale for ordinary and deep-cut songs.")
    heading(f, "Three corrections applied to every candidate", "Each one lowers the score of a song that looks similar only because it is everywhere.")
    # (a) two-way factor
    f.text(24, 84, "1. Two-way check", 13.5, INK, weight="700")
    f.text(24, 102, "Backward score by X's rank in the candidate's list", 11.5, INK2)
    a = Plot(f, 60, 130, 220, 190, (1, 50), (0, 1))
    a.frame([1, 10, 20, 30, 40, 50], [0, 0.5, 1], str, lambda v: f"{v:g}", "X's rank in candidate's list")
    a.line([(r, 1 - (r - 1) / 50) for r in range(1, 51)], BLUE)
    f.line(a.px(1), a.py(0.1), a.px(50), a.py(0.1), ORANGE, 1.8, dash="5 4")
    f.text(a.px(2), a.py(0.1) - 6, "not in list: 0.1", 10.5, ORANGE, "start", "600")
    f.line(a.px(1), a.py(0.5), a.px(50), a.py(0.5), MUTED, 1.4, dash="2 4")
    f.text(a.px(2), a.py(0.5) - 6, "list unavailable: 0.5", 10.5, INK2, "start")
    # (b) breadth
    f.text(340, 84, "2. Breadth discount", 13.5, INK, weight="700")
    f.text(340, 102, "Score of a song listed by n of your songs", 11.5, INK2)
    b = Plot(f, 376, 130, 220, 190, (1, 9), (0, 9))
    b.frame(range(1, 10), [0, 3, 6, 9], str, str, "n = number of your songs listing it")
    b.line([(n, n) for n in range(1, 10)], MUTED)
    b.line([(n, math.sqrt(n)) for n in range(1, 10)], BLUE)
    f.text(b.px(5.6), b.py(5.6) - 8, "plain sum", 11, INK2, "end", "600")
    f.text(b.px(9), b.py(math.sqrt(9)) - 8, "divided by sqrt(n)", 11, BLUE, "end", "600")
    # (c) popularity
    f.text(656, 84, "3. Popularity discount", 13.5, INK, weight="700")
    f.text(656, 102, "Multiplier by popularity vs the typical candidate", 11.5, INK2)
    c = Plot(f, 692, 130, 236, 190, (0.01, 100), (0.05, 10), xlog=True, ylog=True)
    c.frame([0.01, 0.1, 1, 10, 100], [0.1, 1, 10], lambda v: f"{v:g}x", lambda v: f"{v:g}", "popularity, as a multiple of the median")
    clip = lambda v, lo, hi: min(hi, max(lo, v))
    xs = [10 ** (-2 + i * 4 / 80) for i in range(81)]
    base = [(x, clip(x ** -0.3, 0.3, 3)) for x in xs]
    deep = [(x, clip(x ** -0.3, 0.3, 3) * clip(x ** -0.5, 0.2, 3)) for x in xs]
    f.line(c.px(0.01), c.py(1), c.px(100), c.py(1), MUTED, 1, dash="2 4")
    c.line(base, BLUE); c.line(deep, AQUA)
    f.text(c.px(100), c.py(0.3) - 8, "ordinary songs", 11, BLUE, "end", "600")
    f.text(c.px(3), c.py(0.2), "deep cuts", 11, AQUA, "start", "600")
    f.text(24, 392, "Example: a song 10 times as popular as the median keeps 50% of its score. A deep cut that popular keeps about 16%.", 12, INK2)
    return f


def fig08():
    f = Fig(960, 470, "How the 30 playlist songs are chosen",
            "Four slots: 15 confident, 6 deep cuts, 6 explore, 3 wildcard. The right side shows which part of the ranked candidate list each slot draws from.")
    heading(f, "How the 30 playlist songs are chosen", "Four slots with different jobs. The final order is shuffled.")
    slots = [("C", "Confident", 15, BLUE, "#ffffff"), ("D", "Deep cut", 6, AQUA, "#ffffff"),
             ("E", "Explore", 6, ORANGE, "#ffffff"), ("W", "Wildcard", 3, "#6b6a64", "#ffffff")]
    order = [s for s in slots for _ in range(s[2])]
    f.text(24, 88, "The playlist, grouped by slot", 12.5, INK, weight="600")
    for i, (k, nm, n, col, tc) in enumerate(order):
        x, y = 24 + (i % 10) * 34, 100 + (i // 10) * 34
        f.rect(x, y, 30, 30, col, rx=5)
        f.text(x + 15, y + 20, k, 13, tc, "middle", "700")
    rng = random.Random(4)
    shuf = order[:]; rng.shuffle(shuf)
    f.text(24, 224, "The same 30, shuffled into play order", 12.5, INK, weight="600")
    for i, (k, nm, n, col, tc) in enumerate(shuf):
        x, y = 24 + (i % 15) * 22.5, 236 + (i // 15) * 24
        f.rect(x, y, 20, 20, col, rx=3)
        f.text(x + 10, y + 14, k, 10.5, tc, "middle", "700")
    for j, (k, nm, n, col, tc) in enumerate(slots):
        y = 306 + j * 30
        f.rect(24, y, 18, 18, col, rx=4); f.text(33, y + 13, k, 11, tc, "middle", "700")
        f.text(52, y + 14, f"{nm}: {n} songs ({n * 100 // 30}%)", 12, INK2)
    f.text(24, 442, "Shuffling means position says nothing about how a song was chosen.", 11.5, MUTED)
    # right: candidate strip
    f.text(440, 88, "Where each slot draws from", 12.5, INK, weight="600")
    f.text(440, 108, "New-artist candidates, best score on the left", 11.5, INK2)
    n = 60; x0, w, base = 440, 6.9, 205
    for i in range(n):
        h = 70 - 55 * (i / n) ** 0.8
        col = BLUE if i < 15 else (ORANGE if i < 33 else "#a8a79f")
        op = 1 if i < 15 else (0.45 if i < 33 else 0.55)
        f.rect(x0 + i * w, base - h, w - 1.5, h, col, opacity=op)
    for i in (17, 20, 24, 27, 30, 32):
        h = 70 - 55 * (i / n) ** 0.8
        f.rect(x0 + i * w, base - h, w - 1.5, h, ORANGE)
    for i in (38, 47, 56):
        h = 70 - 55 * (i / n) ** 0.8
        f.rect(x0 + i * w, base - h, w - 1.5, h, "#6b6a64")
    f.line(x0, base, x0 + n * w, base, MUTED, 1)
    f.text(x0 + 7.5 * w, base + 16, "C", 12, BLUE, "middle", "700")
    f.text(x0 + 24 * w, base + 16, "E", 12, ORANGE, "middle", "700")
    f.text(x0 + 47 * w, base + 16, "W", 12, "#6b6a64", "middle", "700")
    rows = [(BLUE, "C  Confident", "The top 15 by score, always included."),
            (AQUA, "D  Deep cut", "6 drawn at random from the best 18 songs by artists you already like."),
            (ORANGE, "E  Explore", "6 drawn from the next 18 new songs. Higher scores are more likely."),
            ("#6b6a64", "W  Wildcard", "3 drawn evenly from everything left. Tests what the scores miss.")]
    for j, (col, t, d) in enumerate(rows):
        y = 262 + j * 52
        f.rect(440, y, 6, 40, col, rx=2)
        f.text(456, y + 15, t, 12.5, INK, weight="700")
        f.text(456, y + 33, d, 11.5, INK2)
    return f


def _replay(runs=3000):
    from collections import Counter
    from radio.recommend.candidates.picker import _generate
    cands = [dict(track_uri=f"n{i}", artist=f"a{i}", score=100 - i * 0.9) for i in range(80)]
    cands += [dict(track_uri=f"d{i}", artist=f"b{i}", score=60 - i * 2, kind="deepcut") for i in range(16)]
    rng, cnt = random.Random(3), Counter()
    for _ in range(runs):
        cnt.update(o["track_uri"] for o in _generate(cands, 30, 0.5, 0.2, 0.2, rng, 2, 1.0))
    return [cnt[f"n{i}"] / runs for i in range(80)], [cnt[f"d{i}"] / runs for i in range(16)]


def fig09():
    new, deep = _replay()
    f = Fig(960, 440, "Every pick has a recorded chance of being chosen",
            "Measured by replaying the playlist builder 3000 times: top songs are always chosen, explore band songs about a third of the time, tail songs rarely. Right: why recording the chance lets rare picks be weighted fairly.")
    heading(f, "Every pick has a recorded chance of being chosen", "Measured by running the real playlist builder 3000 times on 80 example songs plus 16 deep cuts.")
    pl = Plot(f, 70, 110, 470, 240, (1, 80), (0, 1))
    pl.frame([1, 15, 33, 50, 80], [0, 0.25, 0.5, 0.75, 1], str, lambda v: f"{v:.0%}", "candidate rank (1 = best score)", "chance of being in the playlist")
    for i, v in enumerate(new):
        f.circle(pl.px(i + 1), pl.py(v), 3.4, BLUE)
    for i, v in enumerate(deep):
        f.rect(pl.px(1 + i * 4.7) - 3.5, pl.py(v) - 3.5, 7, 7, AQUA)
    f.text(pl.px(17.5), pl.py(1) + 4, "always in (confident)", 11.5, BLUE, "start", "600")
    f.text(pl.px(24), pl.py(new[24]) - 16, "sometimes (explore)", 11.5, ORANGE, "middle", "600")
    f.text(pl.px(62), pl.py(new[62]) - 22, "rarely (wildcard)", 11.5, INK2, "middle", "600")
    f.circle(300, 408, 4, BLUE); f.text(310, 412, "new-artist song", 11.5, INK2)
    f.rect(420, 404, 8, 8, AQUA); f.text(434, 412, "deep cut (spread over the axis)", 11.5, INK2)
    # right: inverse weighting
    f.text(590, 96, "Why the chance is recorded", 13.5, INK, weight="700")
    f.lines(590, 120, ["Suppose a song had a 1 in 20 chance of", "being picked, and you loved it."], 12, 16, fill=INK2)
    for i in range(20):
        x, y = 590 + (i % 10) * 34, 168 + (i // 10) * 34
        f.rect(x, y, 28, 28, BLUE if i == 3 else "#ffffff", BLUE if i == 3 else BORDER, rx=5, sw=1.5, dash=None if i == 3 else "3 3")
    f.lines(590, 252, ["The one shown stands in for roughly 20 similar", "songs that could have been shown but were not.",
                      "Counting it 20 times (1 divided by its chance)", "corrects for the picks you never saw."], 12, 17, fill=INK2)
    f.rect(590, 330, 340, 70, GREY_T, BORDER, rx=8)
    f.lines(604, 354, ["Without the recorded chance, the confident", "picks would always look better than they are."], 12, 17, fill=INK)
    return f


FIGS = {"06-two-way-check": fig06, "07-three-corrections": fig07, "08-playlist-slots": fig08,
        "09-selection-chance": fig09}
