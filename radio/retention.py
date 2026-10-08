"""Retention and disconnect for Spotify-derived data (Spotify developer terms: keep content only as long as needed).

Defaults purge only the bulky raw payloads and Spotify content caches; plays/saves/labels are your own listening
record and stay unless you ask. Everything is configurable.

  python -m radio privacy                     # report what exists and what a purge would remove
  python -m radio privacy --purge             # apply the default TTLs
  python -m radio privacy --disconnect --yes  # delete ALL Spotify-derived data and the Spotify login token
"""
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone

from radio.recommend.candidates import cache as cache_mod

log = logging.getLogger("retention")
RAW_EVENTS_DAYS = 30           # raw playback-state JSON from the poller
SPOTIFY_CACHE_HOURS = 24       # cached Spotify search results (track names/URIs)
SPOTIFY_TABLES = ("raw_events", "plays", "saves", "follows", "top_items")
DISCONNECT_IDS_TABLES = ("basis_tracks", "track_ids")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _looks_spotify(path: str) -> bool:
    """Legacy Spotify cache files lived beside the MusicBrainz/ListenBrainz ones; recognise them by their content."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False
    return isinstance(data, list) and bool(data) and isinstance(data[0], dict) and "track_uri" in data[0]


def purge_cache(cache_dir: str | None = None, hours: float = SPOTIFY_CACHE_HOURS, now=time.time) -> int:
    d = cache_dir or cache_mod.CACHE_DIR
    n = 0
    sub = os.path.join(d, cache_mod.SPOTIFY_SUBDIR)
    paths = [os.path.join(sub, f) for f in os.listdir(sub)] if os.path.isdir(sub) else []
    legacy = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json")] if os.path.isdir(d) else []
    for p in paths + [p for p in legacy if _looks_spotify(p)]:
        try:
            if p in paths and now() - os.path.getmtime(p) < hours * 3600:
                continue
            os.remove(p); n += 1
        except OSError:
            pass
    return n


def purge(con, raw_days: float = RAW_EVENTS_DAYS, cache_dir: str | None = None, now: datetime | None = None) -> dict:
    """Apply the default TTLs. `con` is the events DB."""
    cutoff = (now or _now()) - timedelta(days=raw_days)
    before = con.execute("SELECT count(*) FROM raw_events").fetchone()[0]
    con.execute("DELETE FROM raw_events WHERE ts < ?", [cutoff])
    after = con.execute("SELECT count(*) FROM raw_events").fetchone()[0]
    return {"raw_events_deleted": before - after, "cache_files_deleted": purge_cache(cache_dir)}


def disconnect(ev_con, ids_con=None, recs_con=None, token_path: str | None = None, cache_dir: str | None = None) -> dict:
    """Delete every Spotify-derived row, the identity map, the recommendation log, cached API responses and the
    OAuth token. Open-data (MusicBrainz/ListenBrainz) caches are removed too: they are keyed by your listening."""
    out = {}
    for t in SPOTIFY_TABLES:
        out[t] = ev_con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        ev_con.execute(f"DELETE FROM {t}")
    if ids_con is not None:
        for t in DISCONNECT_IDS_TABLES:
            out[t] = ids_con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            ids_con.execute(f"DELETE FROM {t}")
    if recs_con is not None:
        out["picks"] = recs_con.execute("SELECT count(*) FROM picks").fetchone()[0]
        recs_con.execute("DELETE FROM picks")
    d = cache_dir or cache_mod.CACHE_DIR
    out["cache_files"] = sum(len(f) for _, _, f in os.walk(d)) if os.path.isdir(d) else 0
    shutil.rmtree(d, ignore_errors=True)
    tok = token_path
    if tok is None:
        from radio.collect.poller import CACHE as tok
    out["token_removed"] = os.path.exists(tok)
    if os.path.exists(tok):
        os.remove(tok)
    for c in (ev_con, ids_con, recs_con):
        if c is not None:
            c.execute("CHECKPOINT")
    return out


def main(argv):
    from radio.db import connect, connect_ids, connect_recs
    try:
        ev = connect()
    except Exception as e:
        print(f"cannot open the events DB (is the tracker running? stop it first): {e}")
        return 1
    if "--disconnect" in argv:
        if "--yes" not in argv:
            print("This deletes ALL Spotify-derived data (plays, saves, raw events, identity map, recommendation log, "
                  "caches) and your Spotify login token. Re-run with --yes to proceed. "
                  "Also remove the app at https://www.spotify.com/account/apps/ to revoke access.")
            return 2
        print(disconnect(ev, connect_ids(), connect_recs()))
        return 0
    if "--purge" in argv:
        print(purge(ev))
        return 0
    cutoff = _now() - timedelta(days=RAW_EVENTS_DAYS)
    print("raw_events older than", RAW_EVENTS_DAYS, "days:",
          ev.execute("SELECT count(*) FROM raw_events WHERE ts < ?", [cutoff]).fetchone()[0])
    for t in SPOTIFY_TABLES:
        print(f"{t}: {ev.execute(f'SELECT count(*) FROM {t}').fetchone()[0]} rows")
    print("run with --purge to apply the TTLs, --disconnect --yes to delete everything")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
