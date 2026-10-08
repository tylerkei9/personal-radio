"""Figures 01-05: the pipeline, plays to labels, save timing, song identity, co-listening."""
import math
from diagram_kit import *


def fig01():
    f = Fig(960, 400, "The whole system in five steps",
            "Spotify plays flow through watch, learn, find, choose into a weekly playlist, and what you play next week feeds back in.")
    heading(f, "The whole system in five steps", "Each step hands a simple result to the next. The loop closes when you listen to the playlist.")
    steps = [("1 Watch", "Record each play", "what, when, how long"),
             ("2 Learn", "Grade each play", "like, dislike, unclear"),
             ("3 Find", "Look up neighbours", "songs listeners pair"),
             ("4 Choose", "Pick 30 songs", "mix of safe and random"),
             ("5 Publish", "Write the playlist", "private, in Spotify")]
    xs = [15 + i * 200 for i in range(5)]
    for (t, s1, s2), x in zip(steps, xs):
        f.rect(x, 130, 130, 110, GREY_T, BORDER, rx=10)
        f.text(x + 65, 162, t, 15, INK, "middle", "700")
        f.text(x + 65, 190, s1, 12.5, INK, "middle")
        f.text(x + 65, 208, s2, 11.5, INK2, "middle")
    for i, lab in enumerate([["plays"], ["likes and", "dislikes"], ["candidate", "songs"], ["30 songs"]]):
        x = xs[i] + 130
        f.arrow(x + 4, 185, x + 66, 185, INK2)
        f.lines(x + 35, 168 - 12 * (len(lab) - 1), lab, 10.5, 12, fill=INK2, anchor="middle")
    # outside sources
    f.rect(15, 66, 130, 40, BLUE_T, BLUE, rx=8)
    f.text(80, 90, "Spotify account", 12.5, INK, "middle", "600")
    f.arrow(80, 108, 80, 128, BLUE)
    f.rect(400, 66, 160, 40, AQUA_T, AQUA, rx=8)
    f.text(480, 90, "Open music databases", 11.5, INK, "middle", "600")
    f.arrow(480, 108, 480, 128, AQUA)
    f.rect(815, 66, 130, 40, BLUE_T, BLUE, rx=8)
    f.text(880, 90, "Spotify account", 12.5, INK, "middle", "600")
    f.arrow(880, 128, 880, 108, BLUE)
    # feedback loop
    f.polyline([(880, 244), (880, 300), (80, 300), (80, 250)], MUTED, 1.8)
    f.arrow(80, 270, 80, 244, MUTED)
    f.text(480, 322, "Feedback loop: what you play from the playlist becomes next week's data", 12.5, INK2, "middle")
    f.text(480, 352, "Steps 1 and 2 run all day. Steps 3 to 5 run when you ask for a playlist (once a week is enough).", 12, MUTED, "middle")
    return f


def fig02():
    f = Fig(960, 470, "How one play becomes a like or a dislike",
            "A 200 second song with six example plays. Skipping early is a stronger dislike than skipping late. Finishing is a like. Stopping mid-song counts as nothing.")
    heading(f, "How one play becomes a like or a dislike", "Example song: 200 seconds long. Bars show how far each play got.")
    x0, pxs = 230, 2.6                       # 2.6 px per second -> 520 px for 200 s
    X = lambda s: x0 + s * pxs
    top, rowh = 112, 44
    # zones
    zones = [(0, 10, ORANGE, 0.55), (10, 30, ORANGE, 0.33), (30, 180, ORANGE, 0.14), (180, 200, BLUE, 0.28)]
    for a, b, c, op in zones:
        f.rect(X(a), top - 12, (b - a) * pxs, rowh * 6 + 12, c, opacity=op)
    for s, lab in [(0, "0 s"), (10, "10 s"), (30, "30 s"), (180, "90% = 180 s"), (200, "end")]:
        f.line(X(s), top - 20, X(s), top + rowh * 6, MUTED, 1, dash="3 3")
        f.text(X(s) - (4 if s == 0 else 0), top - 26, lab, 11, INK2, "end" if s == 0 else "middle")
    plays = [("Skipped at 4 s", 4, "skip", "Strong dislike  (-1.0)", ORANGE),
             ("Skipped at 20 s", 20, "skip", "Dislike  (-0.6)", ORANGE),
             ("Skipped at 2:00", 120, "skip", "Mild dislike  (-0.3)", ORANGE),
             ("Played to the end", 200, "end", "Mild like  (+0.4)", BLUE),
             ("Played to the end, then saved or replayed", 200, "end2", "Strong like  (+1.0)", BLUE),
             ("Stopped at 1:30 (app closed)", 90, "stop", "Ignored  (no evidence)", MUTED)]
    for i, (name, t, kind, out, col) in enumerate(plays):
        y = top + i * rowh + 6
        nm = name if len(name) < 30 else "Finished, then saved or replayed"
        f.text(20, y + 15, nm, 12, INK)
        f.rect(x0, y + 4, 200 * pxs, 14, "#ffffff", BORDER, rx=3)
        f.rect(x0, y + 4, t * pxs, 14, col, rx=3)
        if kind == "skip":
            f.cross_mark(X(t) + 12, y + 11, 5, ORANGE, 2.2)
        elif kind in ("end", "end2"):
            f.tick_mark(X(t) - 14, y + 11, 5, "#ffffff", 2.2)
        else:
            f.rect(X(t) + 6, y + 6, 4, 10, MUTED)
            f.rect(X(t) + 13, y + 6, 4, 10, MUTED)
        f.text(X(200) + 20, y + 16, out, 12.5, INK, weight="600")
    f.text(24, 446, "Thresholds: under 10 s is a strong dislike, 10 to 30 s a dislike, a later skip a mild one. "
                    "Finished means 90% or more of the song.", 12, INK2)
    return f


def fig03():
    f = Fig(960, 430, "A save only counts for plays before it",
            "Three timelines. A save within 7 days after a play upgrades that play. A save made long before a play only shows familiarity. A save made weeks after is too late.")
    heading(f, "A save only counts for plays that came before it", "Why: saving a song you have loved for years says nothing about one particular play today.")
    X = lambda d: 250 + d * 11
    rows = [("A", "Play, then you save it 2 days later", 2, "Counts: the play becomes a strong like.", True),
            ("B", "You saved it long before the play", None, "Does not count as proof. Stored as 'already familiar'.", False),
            ("C", "Play, then you save it 30 days later", 30, "Too late: the play stays a mild like.", False)]
    for i, (k, name, sv, out, ok) in enumerate(rows):
        y = 128 + i * 98
        f.text(24, y - 40, f"{k}. {name}", 13, INK, weight="600")
        f.line(X(-4), y, X(34), y, MUTED, 1.5)
        for d in (0, 7, 14, 21, 28):
            f.line(X(d), y - 4, X(d), y + 4, MUTED, 1)
            if i == 2:
                f.text(X(d), y + 48, f"day {d}", 10.5, MUTED, "middle")
        if i != 1:
            f.rect(X(0), y - 11, 7 * 11, 22, BLUE_T, BLUE, rx=4, dash="4 3")
            f.text(X(7) + 6, y - 15, "7 day window after the play", 10.5, BLUE)
        f.circle(X(0), y, 8, BLUE, "#ffffff", 2)
        f.text(X(0), y + 28, "play", 11, INK, "middle", "600")
        if sv is None:
            f.rect(X(-4) - 30, y - 8, 16, 16, ORANGE, "#ffffff", rx=2, sw=2)
            f.text(X(-4) - 22, y + 28, "save", 11, INK, "middle", "600")
            f.text(X(-4) - 22, y - 16, "a year earlier", 10.5, INK2, "middle")
        else:
            f.rect(X(sv) - 8, y - 8, 16, 16, ORANGE, "#ffffff", rx=2, sw=2)
            f.text(X(sv), y - 16, "save", 11, INK, "middle", "600")
        f.text(X(34) + 26, y + 4, out, 12, INK2)
        (f.tick_mark if ok else f.cross_mark)(X(34) + 10, y, 5, BLUE if ok else ORANGE, 2.4)
    f.circle(300, 408, 6, BLUE, "#ffffff", 1.5); f.text(312, 412, "a play", 11.5, INK2)
    f.rect(380, 401, 13, 13, ORANGE, "#ffffff", rx=2); f.text(400, 412, "a save (added to Liked Songs)", 11.5, INK2)
    return f


def fig04():
    f = Fig(960, 360, "Matching one song across services",
            "A Spotify link is converted to an ISRC recording code, then to a MusicBrainz recording ID and artist ID. About 79 percent of the songs in the library matched.")
    heading(f, "Matching one song across services", "Spotify, MusicBrainz and ListenBrainz label songs differently. A recording code is the bridge.")
    xs = [20, 275, 530, 785]
    names = [("Spotify link", "spotify:track:...", "Spotify's own label", BLUE_T, BLUE),
             ("ISRC code", "QZ5C81600003", "Barcode of a recording", GREY_T, BORDER),
             ("Recording ID", "d90934be-302a-...", "MusicBrainz label (MBID)", AQUA_T, AQUA),
             ("Artist ID", "e520459c-dff4-...", "Who made it (MBID)", AQUA_T, AQUA)]
    for (t, ex, note, fill, st), x in zip(names, xs):
        f.rect(x, 90, 155, 100, fill, st, rx=10)
        f.text(x + 77, 118, t, 14, INK, "middle", "700")
        f.text(x + 77, 145, ex, 12.5, INK2, "middle")
        f.text(x + 77, 170, note, 11, INK2, "middle")
    labels = [["one Spotify", "lookup"], ["search", "MusicBrainz"], ["read the", "credits"]]
    for i, lab in enumerate(labels):
        x = xs[i] + 155
        f.arrow(x + 3, 145, x + 97, 145, INK2)
        f.lines(x + 50, 128, lab, 10.5, 12, fill=INK2, anchor="middle")
    # match-rate bar
    f.text(24, 235, "How many songs matched (172 songs in the library):", 13, INK, weight="600")
    W = 700; matched = 136 / 172
    f.rect(24, 250, W, 26, ORANGE_T, ORANGE, rx=4)
    f.rect(24, 250, W * matched, 26, AQUA, rx=4)
    f.text(24 + W * matched / 2, 268, "136 matched (79%)", 13, "#ffffff", "middle", "700")
    f.text(24 + W * matched + (W * (1 - matched)) / 2, 268, "36 not found", 12.5, INK, "middle", "600")
    f.text(24, 308, "Unmatched songs are not used as starting points for finding new music. This is why the candidate pool is smaller than the library.", 12, INK2)
    f.text(24, 330, "The codes shown are examples. Coverage depends on how well MusicBrainz knows each recording.", 11.5, MUTED)
    return f


def fig05():
    f = Fig(960, 450, "Where 'similar songs' come from",
            "Left: three listening sessions from other people. Songs that appear together often are neighbours. Right: the resulting neighbour map around one of your songs, with closer rings meaning stronger pairing.")
    heading(f, "Where 'similar songs' come from", "No audio analysis is involved. Neighbours are songs that other listeners play in the same sitting.")
    f.text(24, 84, "Step 1: other people's listening sessions", 13, INK, weight="600")
    sess = [["A", "X", "C", "Y", "E"], ["F", "X", "Y", "G", "H"], ["X", "J", "K", "L", "M"]]
    for r, row in enumerate(sess):
        y = 108 + r * 70
        f.text(24, y + 25, f"Session {r + 1}", 11.5, INK2)
        for c, s in enumerate(row):
            x = 100 + c * 52
            fill, st, tc = GREY_T, BORDER, INK2
            if s == "X": fill, st, tc = BLUE, "#ffffff", "#ffffff"
            if s == "Y": fill, st, tc = AQUA, "#ffffff", "#ffffff"
            f.rect(x, y, 42, 36, fill, st, rx=6, sw=1.5)
            f.text(x + 21, y + 24, s, 14, tc, "middle", "700")
    f.rect(100, 330, 14, 14, BLUE, rx=3); f.text(122, 342, "X = your song", 11.5, INK2)
    f.rect(230, 330, 14, 14, AQUA, rx=3); f.text(252, 342, "Y = a candidate", 11.5, INK2)
    f.text(24, 376, "X and Y appear together in 2 of the 3 sessions.", 12.5, INK)
    f.text(24, 396, "Repeated over millions of sessions, this gives each song a ranked list", 12, INK2)
    f.text(24, 414, "of neighbours with a score.", 12, INK2)
    f.arrow(380, 220, 470, 220, INK2); f.text(425, 208, "count pairs", 11, INK2, "middle")
    f.text(500, 84, "Step 2: the neighbour map for X", 13, INK, weight="600")
    cx, cy = 730, 262
    for r, lab in [(60, "strong"), (100, "medium"), (140, "weak")]:
        f.circle(cx, cy, r, "none", BORDER, 1.2)
        f.text(cx + r * 0.62 + 3, cy + r * 0.78 + 4, lab, 10.5, MUTED)
    nodes = [("Y", 60, -30, AQUA, 3.4), ("N2", 60, 100, GREY_T, 2.6), ("N3", 100, 200, GREY_T, 2.0), ("N4", 100, 150, GREY_T, 2.0),
             ("N5", 100, 300, GREY_T, 1.6), ("N6", 140, 10, GREY_T, 1.2), ("N7", 140, 245, GREY_T, 1.0), ("N8", 140, 118, GREY_T, 1.0)]
    for lab, r, deg, col, w in nodes:
        a = math.radians(deg)
        nx, ny = cx + r * math.cos(a), cy + r * math.sin(a)
        f.line(cx, cy, nx, ny, INK2 if col == GREY_T else AQUA, w)
        f.circle(nx, ny, 15, col, BORDER if col == GREY_T else "#ffffff", 1.5)
        f.text(nx, ny + 4.5, lab, 11.5, INK if col == GREY_T else "#ffffff", "middle", "700")
    f.circle(cx, cy, 22, BLUE, "#ffffff", 2)
    f.text(cx, cy + 5, "X", 16, "#ffffff", "middle", "700")
    f.text(730, 440, "Line thickness = how often the pair is played together", 11.5, INK2, "middle")
    return f


FIGS = {"01-pipeline": fig01, "02-play-to-label": fig02, "03-save-timing": fig03, "04-song-identity": fig04,
        "05-co-listening": fig05}
