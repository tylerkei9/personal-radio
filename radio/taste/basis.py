"""The taste basis: liked songs plus playlists you choose to merge in (config: taste_basis.json).

    {"playlists": {"Chill": "<playlist id>"}}

Merging is local to this tool: nothing is added to your Spotify library. Tracks are deduplicated across sources,
keeping the most recent added_at. Stored minimally (URI + added_at) in the identity DB.
"""
import json
import os
from datetime import datetime

from radio import paths

CONFIG = paths.TASTE_BASIS


def load_config(path: str = CONFIG) -> dict[str, str]:
    try:
        with open(path) as f:
            return json.load(f).get("playlists", {})
    except (OSError, ValueError):
        return {}


def _ts(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None) if s else None


def playlist_tracks(sp, playlist_id: str) -> list[tuple[str, datetime | None]]:
    """(track_uri, added_at) for every real track in a playlist you own. Handles the Feb-2026 `item` key
    (older responses used `track`); skips episodes and local files."""
    out, off = [], 0
    while True:
        page = sp._get(f"playlists/{playlist_id}/items", limit=50, offset=off)
        for it in page["items"]:
            t = it.get("item") or it.get("track") or {}
            uri = t.get("uri") or ""
            if uri.startswith("spotify:track:") and not it.get("is_local"):
                out.append((uri, _ts(it.get("added_at"))))
        if not page.get("next"):
            return out
        off += 50


def sync_basis(sp, ids_con, ev_con, playlists: dict[str, str] | None = None) -> dict[str, int]:
    """Rebuild basis_tracks from liked songs + configured playlists. Returns row counts per source."""
    playlists = load_config() if playlists is None else playlists
    ids_con.execute("DELETE FROM basis_tracks")
    rows = [("liked", uri, ts) for ts, uri in ev_con.execute("SELECT ts, track_uri FROM saves").fetchall()]
    for name, pid in playlists.items():
        rows += [(f"playlist:{name}", uri, ts) for uri, ts in playlist_tracks(sp, pid)]
    ids_con.executemany("INSERT OR REPLACE INTO basis_tracks VALUES (?,?,?)", rows)
    counts = {}
    for src, _, _ in rows:
        counts[src] = counts.get(src, 0) + 1
    return counts
