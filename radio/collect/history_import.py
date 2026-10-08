"""Import Spotify Extended Streaming History (Streaming_History_Audio_*.json).

Usage: python -m radio import-history path/to/dir_or_zip
"""
import glob
import json
import os
import sys
import zipfile
from datetime import datetime


START_MAP = {"clickrow": "user", "playbtn": "user", "remote": "user", "appload": "user",
             "trackdone": "auto", "fwdbtn": "nav", "backbtn": "nav"}
END_MAP = {"trackdone": "completed", "fwdbtn": "skipped", "backbtn": "skipped"}


def map_end(reason_end: str | None, skipped: bool | None) -> str:
    if reason_end in END_MAP:
        return END_MAP[reason_end]
    if skipped:
        return "skipped"
    return "other"


def parse_row(r: dict):
    """Return a plays-row tuple, or None for podcasts/episodes/blank rows."""
    uri = r.get("spotify_track_uri")
    if not uri:
        return None
    ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).replace(tzinfo=None)
    return (
        "history", ts, uri,
        r.get("master_metadata_track_name"), r.get("master_metadata_album_artist_name"),
        None, None, int(r.get("ms_played") or 0),
        map_end(r.get("reason_end"), r.get("skipped")),
        r.get("platform"), None, r.get("shuffle"), bool(r.get("incognito_mode")),
        START_MAP.get(r.get("reason_start"), "other"), None, None,
    )


def _load_json_blobs(path: str):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if "Streaming_History_Audio" in n and n.endswith(".json"):
                    yield json.loads(z.read(n))
    else:
        for f in sorted(glob.glob(os.path.join(path, "**", "Streaming_History_Audio*.json"), recursive=True)):
            with open(f, encoding="utf-8") as fh:
                yield json.load(fh)


def import_history(path: str, con=None) -> int:
    from radio.db import connect
    con = con or connect()
    rows = [p for blob in _load_json_blobs(path) for r in blob if (p := parse_row(r))]
    con.executemany(
        "INSERT OR IGNORE INTO plays VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


if __name__ == "__main__":
    print(f"imported {import_history(sys.argv[1])} plays")
