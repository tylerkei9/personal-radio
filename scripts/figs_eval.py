"""Figures 10-14: honest testing, ranking score, polling, taste weights, data flow."""
import math
import os
import random
import sys
from diagram_kit import *
from figs_logic import Plot

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fig10():
    f = Fig(960, 440, "Testing on the future, not on a shuffle",
            "Top: a random split lets the model train on plays that happened after the ones it is tested on. Bottom: a rolling split always trains on the past and tests on what came next, with a small gap.")
    heading(f, "Testing on the future, not on a shuffle", "Each square is one day of listening. Time runs left to right.")
    n, x0, w = 24, 130, 28
    rng = random.Random(8)
    test = set(rng.sample(range(n), 5))
    f.text(24, 88, "Random split (misleading)", 13, INK, weight="700")
    for i in range(n):
        x = x0 + i * w
        if i in test:
            f.rect(x, 100, w - 3, 30, ORANGE_T, ORANGE, rx=4, sw=2); f.text(x + 12, 120, "T", 11, ORANGE, "middle", "700")
        else:
            f.rect(x, 100, w - 3, 30, BLUE_T, BLUE, rx=4)
    t = sorted(test)[1]
    f.arrow(x0 + (t + 6) * w, 142, x0 + t * w + 10, 134, INK2, 1.6)
    f.text(x0 + (t + 6) * w + 6, 158, "the model trains on a later day than the one it is tested on", 11.5, INK2)
    f.text(x0, 180, "It has seen the future, so the score looks better than it would be in real use.", 12, INK2)
    f.text(24, 222, "Rolling split (what this project uses)", 13, INK, weight="700")
    for k, cut in enumerate([10, 14, 18]):
        y = 240 + k * 44
        f.text(24, y + 20, f"Test {k + 1}", 11.5, INK2)
        for i in range(n):
            x = x0 + i * w
            if i < cut - 1:
                f.rect(x, y, w - 3, 30, BLUE_T, BLUE, rx=4)
            elif i == cut - 1:
                f.rect(x, y, w - 3, 30, "#ffffff", MUTED, rx=4, dash="3 3")
            elif i == cut:
                f.rect(x, y, w - 3, 30, ORANGE_T, ORANGE, rx=4, sw=2); f.text(x + 12, y + 20, "T", 11, ORANGE, "middle", "700")
            else:
                f.rect(x, y, w - 3, 30, GREY_T, BORDER, rx=4, opacity=0.6)
    f.rect(130, 396, 14, 14, BLUE_T, BLUE, rx=3); f.text(150, 408, "train (past)", 11.5, INK2)
    f.rect(250, 396, 14, 14, "#ffffff", MUTED, rx=3, dash="3 3"); f.text(270, 408, "gap", 11.5, INK2)
    f.rect(320, 396, 14, 14, ORANGE_T, ORANGE, rx=3, sw=2); f.text(340, 408, "T = test day", 11.5, INK2)
    f.rect(430, 396, 14, 14, GREY_T, BORDER, rx=3); f.text(450, 408, "not used yet", 11.5, INK2)
    return f


def fig11():
    f = Fig(960, 440, "Scoring a ranked list: why position matters",
            "Two ranked lists of 10 songs each contain the same 2 liked songs. List A has them at positions 1 and 4, list B at positions 7 and 9. A bar chart shows the weight of each position and the resulting scores.")
    heading(f, "Scoring a ranked list: why position matters", "NDCG@10 gives more credit to a hit near the top. Both lists below contain the same two liked songs.")
    w = [1 / math.log2(i + 2) for i in range(10)]
    ideal = w[0] + w[1]
    A, B = {0, 3}, {6, 8}
    sa, sb = sum(w[i] for i in A) / ideal, sum(w[i] for i in B) / ideal
    pl = Plot(f, 70, 110, 400, 190, (0.5, 10.5), (0, 1.05))
    pl.frame(range(1, 11), [0, 0.5, 1], str, lambda v: f"{v:g}", "position in the list", "credit for a hit at that position")
    for i in range(10):
        x = pl.px(i + 1)
        f.rect(x - 14, pl.py(w[i]), 28, pl.py(0) - pl.py(w[i]), GREY_T, BORDER, rx=3)
        f.text(x, pl.py(w[i]) - 5, f"{w[i]:.2f}", 10, INK2, "middle")
    for i in range(10):
        x = pl.px(i + 1)
        f.circle(x - 6, pl.py(0) - 12, 6, BLUE if i in A else "#ffffff", BLUE, 1.5) if i in A else None
        f.rect(x + 1, pl.py(0) - 18, 12, 12, ORANGE if i in B else "#ffffff", ORANGE, rx=2, sw=1.5) if i in B else None
    f.circle(120, 372, 6, BLUE); f.text(132, 376, "liked song in list A", 11.5, INK2)
    f.rect(270, 366, 12, 12, ORANGE, rx=2); f.text(288, 376, "liked song in list B", 11.5, INK2)
    f.text(520, 112, "Scores (best possible = 1.00)", 13.5, INK, weight="700")
    for j, (nm, pos, sc, col) in enumerate([("List A", "hits at positions 1 and 4", sa, BLUE), ("List B", "hits at positions 7 and 9", sb, ORANGE)]):
        y = 140 + j * 90
        f.text(520, y + 14, nm, 13, INK, weight="700")
        f.text(580, y + 14, pos, 12, INK2)
        f.rect(520, y + 28, 380, 22, "#ffffff", BORDER, rx=4)
        f.rect(520, y + 28, 380 * sc, 22, col, rx=4)
        f.text(520 + 380 * sc + (8 if sc < 0.8 else -8), y + 45, f"{sc:.2f}", 13, INK if sc < 0.8 else "#ffffff", "start" if sc < 0.8 else "end", "700")
    f.lines(520, 335, ["Best case for two liked songs: positions 1 and 2.",
                      "Credit at position i is 1 / log2(i + 1), then divided by that best case."], 12, 17, fill=INK2)
    f.text(520, 385, "Why it matters: a playlist is read from the top, so late hits are worth less.", 12, INK2)
    return f


def fig12():
    from radio.collect.poller import next_delay, LONG_IDLE_POLLS
    from radio.collect.tracker import Snapshot
    from datetime import datetime
    idle = Snapshot(ts=datetime(2026, 1, 1), is_playing=False)
    t, pts, calls, streak = 0.0, [], 0, 0
    while t < 24 * 3600:
        d = next_delay(idle, streak)
        pts.append((t / 60, d)); t += d; streak += 1; calls += 1
    old_calls = int(24 * 3600 / 10)
    f = Fig(960, 440, "Checking less often when nothing is playing",
            f"Seconds between checks as idle time grows. Idle checks slow from every 10 seconds to every minute and then every 2 minutes. About {calls} checks a day instead of {old_calls}.")
    heading(f, "Checking less often when nothing is playing", "A late check loses nothing: start times come from the song's own progress. Short plays are recovered hourly.")
    pl = Plot(f, 80, 120, 520, 220, (0, 120), (0, 130))
    pl.frame([0, 20, 40, 60, 80, 100, 120], [0, 30, 60, 90, 120], str, str, "minutes since playback stopped", "seconds between checks")
    last = None; poly = []
    for m, d in pts:
        if m > 120: break
        if last is not None: poly.append((pl.px(m), pl.py(last)))
        poly.append((pl.px(m), pl.py(d))); last = d
    f.polyline(poly, BLUE, 2.4)
    f.line(pl.px(0), pl.py(4), pl.px(120), pl.py(4), AQUA, 1.8, dash="5 4")
    f.text(pl.px(118), pl.py(4) - 7, "while a song plays: 4 s", 11, AQUA, "end", "600")
    f.text(pl.px(30), pl.py(60) - 8, "60 s", 11, BLUE, "middle", "600")
    f.text(pl.px(100), pl.py(120) - 8, "120 s after about an hour idle", 11, BLUE, "end", "600")
    f.text(640, 128, "Checks per idle day", 13.5, INK, weight="700")
    for j, (nm, v, col) in enumerate([("Before", old_calls, MUTED), ("Now", calls, BLUE)]):
        y = 150 + j * 56
        f.text(640, y + 16, nm, 12.5, INK, weight="600")
        wbar = 190 * v / old_calls
        f.rect(700, y, wbar, 24, col, rx=4)
        f.text(700 + wbar + 8, y + 17, f"{v:,}", 12.5, INK, weight="700")
    f.lines(640, 290, ["Also: an hourly catch-up reads Spotify's", "recently-played list and fills in anything missed.",
                      "A long silence (computer asleep) triggers it at once."], 12, 17, fill=INK2)
    return f


def fig13():
    f = Fig(960, 420, "Two ways the taste profile avoids being swamped",
            "Left: a liked song's weight halves each year. Right: an artist's total weight grows with the square root of the number of liked songs, so one prolific artist cannot dominate.")
    heading(f, "Two ways the taste profile avoids being swamped", "Both are simple curves, shown here exactly as the program computes them.")
    f.text(24, 84, "1. Older likes count a little less", 13.5, INK, weight="700")
    f.text(24, 102, "Weight of a liked song by its age (half-life: 1 year)", 11.5, INK2)
    a = Plot(f, 64, 132, 360, 200, (0, 3), (0, 1.05))
    a.frame([0, 1, 2, 3], [0, 0.25, 0.5, 0.75, 1], lambda v: f"{v} yr" if v else "new", lambda v: f"{v:g}", "age of the like")
    a.line([(x / 20, 0.5 ** (x / 20)) for x in range(61)], BLUE)
    for yrs in (1, 2):
        f.circle(a.px(yrs), a.py(0.5 ** yrs), 4.5, BLUE, "#ffffff", 1.5)
        f.text(a.px(yrs) + 8, a.py(0.5 ** yrs) - 8, f"{0.5 ** yrs:.2f}", 11.5, INK, weight="700")
    f.text(520, 84, "2. One artist cannot take over", 13.5, INK, weight="700")
    f.text(520, 102, "Artist weight by number of liked songs", 11.5, INK2)
    b = Plot(f, 560, 132, 370, 200, (0, 17), (0, 17))
    b.frame([1, 4, 9, 16], [0, 4, 8, 12, 16], str, str, "liked songs by one artist")
    b.line([(n, n) for n in range(1, 17)], MUTED)
    b.line([(n / 4, math.sqrt(n / 4)) for n in range(4, 65)], BLUE)
    f.text(b.px(9.2), b.py(9.2) - 8, "plain count", 11, INK2, "end", "600")
    f.text(b.px(16.5), b.py(2.2), "square root: 16 songs count as 4", 11, BLUE, "end", "600")
    f.text(24, 392, "Result: an artist with 16 liked songs has 4 times the pull of an artist with 1, not 16 times.", 12, INK2)
    return f


def fig14():
    f = Fig(960, 420, "What stays on your computer and what is sent out",
            "Your computer holds all history and the Spotify login. It sends requests to Spotify, ListenBrainz and MusicBrainz. GitHub receives the code only.")
    heading(f, "What stays on your computer and what is sent out", "Arrows show requests leaving your computer and the kind of data they carry.")
    f.rect(330, 90, 300, 250, GREY_T, BORDER, rx=12)
    f.text(480, 116, "Your computer", 15, INK, "middle", "700")
    items = ["Listening history", "Saved songs and recommendations", "Song identity map", "Spotify login token"]
    for i, t in enumerate(items):
        f.rect(350, 136 + i * 42, 260, 32, "#ffffff", BORDER, rx=6)
        f.text(480, 157 + i * 42, t, 12.5, INK, "middle")
    f.text(480, 322, "Folder: data/  (never uploaded)", 11.5, INK2, "middle")
    ext = [(24, 90, "Spotify", BLUE_T, BLUE, "Reads what you play, saves, and top lists.", "Writes one private playlist."),
           (700, 90, "ListenBrainz", AQUA_T, AQUA, "Receives song codes only.", "Returns songs played together."),
           (700, 190, "MusicBrainz", AQUA_T, AQUA, "Receives recording codes (ISRC).", "Returns song and artist IDs."),
           (24, 240, "GitHub", GREY_T, BORDER, "Receives the program code.", "Never your data or login.")]
    for x, y, nm, fill, st, l1, l2 in ext:
        f.rect(x, y, 236, 90 if nm != "GitHub" else 80, fill, st, rx=10)
        f.text(x + 12, y + 24, nm, 14, INK, weight="700")
        f.text(x + 12, y + 46, l1, 11.5, INK2)
        f.text(x + 12, y + 64, l2, 11.5, INK2)
    f.arrow(262, 150, 326, 170, BLUE); f.arrow(326, 190, 262, 170, BLUE, dash="4 3")
    f.text(294, 146, "reads", 10.5, BLUE, "middle", "600"); f.text(294, 210, "writes playlist", 10, BLUE, "middle")
    f.arrow(634, 150, 696, 140, AQUA); f.arrow(634, 240, 696, 240, AQUA)
    f.text(665, 134, "song codes", 10, INK2, "middle"); f.text(665, 232, "ISRC codes", 10, INK2, "middle")
    f.arrow(326, 285, 264, 285, MUTED, dash="4 3"); f.text(295, 277, "code only", 10, INK2, "middle")
    f.lines(24, 380, ["The open databases receive song and artist codes, not your listening history or account details.", "If you set RADIO_CONTACT, that contact is included in requests to MusicBrainz, as they ask."], 12, 18, fill=INK2)
    return f


FIGS = {"10-test-on-the-future": fig10, "11-ranking-score": fig11, "12-adaptive-checking": fig12,
        "13-taste-weights": fig13, "14-data-flow": fig14}
