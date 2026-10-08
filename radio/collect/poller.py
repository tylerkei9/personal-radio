"""Spotify playback poller. Run on an always-on machine.

Env: SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI (e.g. http://127.0.0.1:8888/callback)
Usage: python -m radio track
"""
import json
import logging
import getpass
import os
import time
from datetime import datetime, timezone

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from radio import paths
from radio.db import connect
from radio.collect.health import write_heartbeat
from radio.collect.tracker import Snapshot, Tracker

SCOPE = ("user-read-playback-state user-read-currently-playing user-read-recently-played "
         "user-library-read user-follow-read user-top-read playlist-modify-private "
         "playlist-read-private playlist-read-collaborative")
CACHE = paths.SPOTIFY_TOKEN
PLAY_COLS = ["source", "started_at", "track_uri", "track_name", "artist", "isrc", "duration_ms",
             "ms_played", "end_reason", "device", "context_uri", "shuffle", "incognito",
             "start_kind", "context_type", "seeks"]


def to_snapshot(pb: dict | None) -> Snapshot:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not pb or not pb.get("item"):
        return Snapshot(ts=now, is_playing=False)
    it = pb["item"]
    return Snapshot(
        ts=now, is_playing=bool(pb.get("is_playing")), track_uri=it.get("uri"),
        name=it.get("name"), artist=(it.get("artists") or [{}])[0].get("name"),
        isrc=(it.get("external_ids") or {}).get("isrc"), duration_ms=it.get("duration_ms"),
        progress_ms=pb.get("progress_ms") or 0,
        device=(pb.get("device") or {}).get("type"),
        context_uri=(pb.get("context") or {}).get("uri"), shuffle=pb.get("shuffle_state"),
        is_podcast=pb.get("currently_playing_type") != "track")


IDLE_LADDER = (10.0, 10.0, 20.0, 30.0, 60.0)   # seconds between polls while nothing is playing, by idle streak
LONG_IDLE_POLLS = 60                             # after this many idle polls (about an hour) poll every 2 minutes
RECONCILE_EVERY_S = 3600
GAP_S = 120                                      # silence longer than this (and 3x the planned delay) = sleep/offline gap


def next_delay(s: Snapshot, idle_streak: int = 0) -> float:
    """Seconds until the next poll. Playing mid-track stays at 4s (skip detection needs it); near the end 1.5s to catch
    the real end. Idle or paused backs off, because a late poll costs nothing: start times derive from progress_ms and
    anything shorter than the gap is recovered by the recently-played reconciler."""
    playing = bool(s.track_uri) and s.is_playing
    if playing:
        if s.duration_ms and s.duration_ms - s.progress_ms < 8_000:
            return 1.5
        return 4.0
    if idle_streak >= LONG_IDLE_POLLS:
        return 120.0
    return IDLE_LADDER[min(idle_streak, len(IDLE_LADDER) - 1)]


def _prompt_missing_env():
    """Ask for any missing SPOTIPY_* credentials (paste them; the secret is not echoed)."""
    defaults = {"SPOTIPY_REDIRECT_URI": "http://127.0.0.1:8888/callback"}
    for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        if os.environ.get(name):
            continue
        ask = getpass.getpass if name.endswith("SECRET") else input
        hint = f" [{defaults[name]}]" if name in defaults else ""
        os.environ[name] = ask(f"{name}{hint}: ").strip() or defaults.get(name, "")


def build_client(timeout: float = 10) -> spotipy.Spotify:
    _prompt_missing_env()
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(scope=SCOPE, cache_path=CACHE, open_browser=True, requests_timeout=timeout),
        retries=0, requests_timeout=timeout)


def is_gap(elapsed_s: float, planned_delay_s: float) -> bool:
    return elapsed_s > max(GAP_S, 3 * planned_delay_s)


def loop(sp: spotipy.Spotify, con, reconcile=None):
    """Poll forever. `reconcile(sp, con)` (e.g. sync.backfill_recent) runs hourly and right after any gap."""
    log = logging.getLogger("poller")
    tr, backoff, idle, delay = Tracker(), 0.0, 0, 4.0
    last_poll = last_reconcile = time.monotonic()
    while True:
        now = time.monotonic()
        gap = is_gap(now - last_poll, delay)
        if gap:
            log.warning("no poll for %.0fs (sleep/offline?)", now - last_poll)
            con.execute("INSERT INTO raw_events VALUES (?,?,?)",
                        [datetime.now(timezone.utc).replace(tzinfo=None), "gap", json.dumps({"seconds": round(now - last_poll)})])
        last_poll = now
        due = bool(reconcile) and (gap or now - last_reconcile >= RECONCILE_EVERY_S)
        try:
            pb = sp.current_playback(additional_types="episode")
            backoff = 0.0
        except spotipy.SpotifyException as e:
            backoff = float((e.headers or {}).get("Retry-After", 30)) + 1 if e.http_status == 429 \
                else min((backoff or 5) * 2, 300)
            reason = "QUOTA_EXCEEDED" if "QUOTA_EXCEEDED" in str(e) else None   # quota is shared across the developer account
            log.warning("spotify error %s%s, sleeping %ss", e.http_status, f" ({reason})" if reason else "", backoff)
            write_heartbeat(status="rate_limited" if e.http_status == 429 else "error", error=reason or str(e.http_status))
            delay = backoff
            time.sleep(backoff)
            continue
        except Exception as e:  # network blips (sleep/wake, wifi): keep going
            backoff = min((backoff or 5) * 2, 300)
            log.warning("poll failed (%s), sleeping %ss", e, backoff)
            write_heartbeat(status="error", error=type(e).__name__)
            delay = backoff
            time.sleep(backoff)
            continue
        s = to_snapshot(pb)
        write_heartbeat(status="playing" if s.is_playing else "idle", track=s.track_uri)
        con.execute("INSERT INTO raw_events VALUES (?,?,?)",
                    [s.ts, "poll", json.dumps(pb) if pb else "null"])
        tr.update(s)
        idle = idle + 1 if not (s.track_uri and s.is_playing) else 0
        delay = next_delay(s, idle)
        for p in tr.drain():
            con.execute(f"INSERT OR IGNORE INTO plays VALUES ({','.join('?'*len(PLAY_COLS))})",
                        [p[c] for c in PLAY_COLS])
            log.info("%s/%s %s - %s (%sms)", p["start_kind"], p["end_reason"], p["artist"],
                     p["track_name"], p["ms_played"])
        if due:       # after the poll's own plays are stored, so the reconciler can see them and not duplicate
            last_reconcile = time.monotonic()
            try:
                log.info("reconcile: %s plays recovered", reconcile(sp, con))
            except Exception as e:
                log.warning("reconcile failed: %s", e)
        time.sleep(delay)


def main():
    loop(build_client(), connect())


if __name__ == "__main__":
    main()
