"""Plays -> labelled training rows. Pure logic (`build_rows`) plus a thin DB loader."""
from datetime import datetime, timedelta

from radio.taste.labels import label_play

REPEAT_WINDOW = timedelta(hours=24)
SAVE_WINDOW = timedelta(days=7)    # a like only upgrades a play's label if it follows the play within this window
# Every play weighs the same. How it started (user / auto / nav, intent) is a feature, not a weight: autoplay is
# exactly the exposure a recommender gets judged on, so it must not count for less than hand-picked plays.


def mark_repeats(plays: list[dict]) -> set[tuple]:
    """Keys (started_at, track_uri) of plays whose track was played again within REPEAT_WINDOW."""
    last_seen, out = {}, set()
    for p in sorted(plays, key=lambda p: p["started_at"], reverse=True):
        nxt = last_seen.get(p["track_uri"])
        if nxt is not None and nxt - p["started_at"] <= REPEAT_WINDOW:
            out.add((p["started_at"], p["track_uri"]))
        last_seen[p["track_uri"]] = p["started_at"]
    return out


def is_intent(p: dict) -> bool:
    return p.get("start_kind") == "user" and (p.get("context_type") in ("artist", "album") or not p.get("context_uri"))


def build_rows(plays: list[dict], saved_at: dict[str, datetime] | set[str]) -> list[dict]:
    """Attach label and features to each play; plays with no usable label are dropped.

    `saved_at` maps track_uri -> when it was liked. Leakage rule: a save upgrades the label only if it came
    after the play (within SAVE_WINDOW); a save that predates the play is the feature `saved_asof_play`.
    (A bare set of URIs has no timestamps, so it can only mean "saved before", i.e. feature only.)"""
    saved_at = saved_at if isinstance(saved_at, dict) else {u: None for u in saved_at}
    repeats = mark_repeats(plays)
    rows = []
    for p in plays:
        ts, when = p["started_at"], saved_at.get(p["track_uri"])
        before = p["track_uri"] in saved_at and (when is None or when < ts)
        after = when is not None and ts <= when <= ts + SAVE_WINDOW
        lab = label_play(p.get("ms_played") or 0, p.get("duration_ms"), p["end_reason"],
                         saved=after, repeated=(ts, p["track_uri"]) in repeats,
                         incognito=bool(p.get("incognito")))
        if lab is None:
            continue
        rows.append({**p, "label": lab.value, "label_name": lab.name, "weight": 1.0,
                     "saved_asof_play": before, "saved_within_window": after, "intent": is_intent(p)})
    return rows


def load_rows(con) -> list[dict]:
    cur = con.execute("SELECT * FROM plays ORDER BY started_at")
    cols = [d[0] for d in cur.description]
    plays = [dict(zip(cols, r)) for r in cur.fetchall()]
    saved = {u: ts for ts, u in con.execute("SELECT ts, track_uri FROM saves").fetchall()}
    return build_rows(plays, saved)
