"""Startup ingest + periodic library sync: recently played backfill, saves, follows, top items.

Each step is isolated: Spotify has been removing endpoints, so one failing must not stop the rest.
"""
import logging
from datetime import datetime, timedelta, timezone

from radio.collect.tracker import context_type

log = logging.getLogger("sync")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


RECENT_SLACK = timedelta(seconds=90)


def missing_recent(items: list[dict], existing: list[tuple]) -> list[dict]:
    """Recently-played items with no matching play already stored. `existing` = (track_uri, started_at, ms_played)
    rows. An item matches a stored play of the same track whose [started_at, started_at + duration] window, widened
    by RECENT_SLACK, contains the item's played_at (Spotify stamps it near the play's end). Window matching, not
    "newer than the last play", so the live poller and this reconciler never double-count a play."""
    by_uri = {}
    for uri, started, _ in existing:
        by_uri.setdefault(uri, []).append(started)
    out = []
    for it in items:
        t = it["track"]
        played_at = datetime.fromisoformat(it["played_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        dur = timedelta(milliseconds=t.get("duration_ms") or 0)
        if any(started - RECENT_SLACK <= played_at <= started + dur + RECENT_SLACK for started in by_uri.get(t["uri"], [])):
            continue
        out.append({**it, "_played_at": played_at})
    return out


def backfill_recent(sp, con) -> int:
    """Fill gaps (app off, laptop asleep, short plays between polls) from the last-50 recently-played list.
    ms_played/skip info is unknown there, so end_reason='other' (counts as exposure, not a label).
    Safe to run any time, as often as hourly: already-recorded plays are skipped."""
    items = sp.current_user_recently_played(limit=50).get("items", [])
    existing = con.execute("SELECT track_uri, started_at, ms_played FROM plays").fetchall()
    n = 0
    for it in missing_recent(items, existing):
        t, played_at = it["track"], it["_played_at"]
        ctx = (it.get("context") or {}).get("uri")
        con.execute("INSERT OR IGNORE INTO plays VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            "recent", played_at, t["uri"], t["name"], t["artists"][0]["name"],
            (t.get("external_ids") or {}).get("isrc"), t.get("duration_ms"), None, "other",
            None, ctx, None, False, "other", context_type(ctx), None])
        n += 1
    return n


def sync_saves(sp, con) -> int:
    n, off = 0, 0
    while True:
        page = sp.current_user_saved_tracks(limit=50, offset=off)
        for it in page["items"]:
            ts = datetime.fromisoformat(it["added_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            con.execute("INSERT OR REPLACE INTO saves VALUES (?,?)", [ts, it["track"]["uri"]])
            n += 1
        if not page.get("next"):
            return n
        off += 50


def sync_follows(sp, con) -> int:
    n, after = 0, None
    while True:
        res = sp.current_user_followed_artists(limit=50, after=after)["artists"]
        for a in res["items"]:
            con.execute("INSERT OR REPLACE INTO follows VALUES (?,?,?)", [a["uri"], a["name"], _now()])
            n += 1
        after = res.get("cursors", {}).get("after")
        if not after:
            return n


def sync_top(sp, con) -> int:
    n, now = 0, _now()
    con.execute("DELETE FROM top_items")
    for rng in ("short_term", "medium_term", "long_term"):
        for kind, fn in (("artist", sp.current_user_top_artists), ("track", sp.current_user_top_tracks)):
            for i, it in enumerate(fn(limit=50, time_range=rng)["items"]):
                con.execute("INSERT INTO top_items VALUES (?,?,?,?,?,?)",
                            [kind, rng, i + 1, it["uri"], it["name"], now])
                n += 1
    return n


def run_all(sp, con):
    for step in (backfill_recent, sync_saves, sync_follows, sync_top):
        try:
            log.info("%s: %s rows", step.__name__, step(sp, con))
        except Exception as e:
            log.warning("%s failed: %s", step.__name__, e)
