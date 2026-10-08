"""Event store (DuckDB). Raw events are append-only; plays are derived and re-derivable."""
import os
import duckdb

from radio import paths

DB_PATH = os.environ.get("RADIO_DB", paths.EVENTS_DB)

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_events (
    ts TIMESTAMP, kind VARCHAR, payload JSON
);
CREATE TABLE IF NOT EXISTS plays (
    source VARCHAR,            -- 'poller' | 'history'
    started_at TIMESTAMP,
    track_uri VARCHAR,
    track_name VARCHAR,
    artist VARCHAR,
    isrc VARCHAR,
    duration_ms INTEGER,       -- NULL for history import
    ms_played INTEGER,
    end_reason VARCHAR,        -- completed | skipped | other
    device VARCHAR,            -- platform / device type
    context_uri VARCHAR,
    shuffle BOOLEAN,
    incognito BOOLEAN,
    start_kind VARCHAR,        -- user | auto | nav | other
    context_type VARCHAR,      -- artist | album | playlist | show | collection | NULL (single track)
    seeks INTEGER,
    PRIMARY KEY (source, started_at, track_uri)
);
CREATE TABLE IF NOT EXISTS saves (
    ts TIMESTAMP, track_uri VARCHAR, PRIMARY KEY (track_uri)
);
CREATE TABLE IF NOT EXISTS follows (
    artist_uri VARCHAR PRIMARY KEY, name VARCHAR, ts TIMESTAMP
);
CREATE TABLE IF NOT EXISTS top_items (
    kind VARCHAR, time_range VARCHAR, rank INTEGER, uri VARCHAR, name VARCHAR, fetched_at TIMESTAMP
);
-- Proxy for "searched for it and chose it": hand-started plays from artist/album pages or as a lone track.
-- (Spotify exposes no search history; history imports can't separate search clicks from playlist clicks.)
CREATE OR REPLACE VIEW intent_plays AS
SELECT * FROM plays
WHERE start_kind = 'user' AND (context_type IN ('artist', 'album') OR context_uri IS NULL);
"""


IDS_PATH = os.environ.get("RADIO_IDS_DB", paths.IDS_DB)

# Identity cache lives in its own file: no lock contention with the tracker, and Spotify-derived
# event data stays separate from open-data (MusicBrainz) identifiers.
IDS_SCHEMA = """
-- Identity cache: Spotify URI <-> ISRC <-> MusicBrainz. mb_checked_at set even on a miss, so misses aren't retried.
-- The taste basis: liked songs plus any playlists merged in (taste_basis.json). Minimal Spotify data: URI + added_at.
CREATE TABLE IF NOT EXISTS basis_tracks (
    source VARCHAR, track_uri VARCHAR, added_at TIMESTAMP, PRIMARY KEY (source, track_uri)
);
CREATE TABLE IF NOT EXISTS track_ids (
    track_uri VARCHAR PRIMARY KEY, isrc VARCHAR, recording_mbid VARCHAR, artist_mbid VARCHAR,
    isrc_checked_at TIMESTAMP, mb_checked_at TIMESTAMP
);
"""


def connect_ids(path: str | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(path or IDS_PATH)
    con.execute(IDS_SCHEMA)
    return con


def connect(path: str | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(path or DB_PATH)
    con.execute(SCHEMA)
    return con


def connect_snapshot() -> duckdb.DuckDBPyConnection:
    """Read-only view of the DB while the tracker holds the write lock (copies the file + WAL)."""
    import shutil, tempfile
    d = tempfile.mkdtemp(prefix="radio_snap_")
    for suffix in ("", ".wal"):
        if os.path.exists(DB_PATH + suffix):
            shutil.copy(DB_PATH + suffix, os.path.join(d, "radio.duckdb" + suffix))
    return duckdb.connect(os.path.join(d, "radio.duckdb"), read_only=True)


RECS_PATH = os.environ.get("RADIO_RECS_DB", paths.RECS_DB)

# Every recommendation the system makes, with why and with what probability (needed for off-policy evaluation
# and to tag later plays as recommender-sourced). Own file: no lock contention with the tracker.
RECS_SCHEMA = """
CREATE TABLE IF NOT EXISTS picks (
    playlist_id VARCHAR, created_at TIMESTAMP, position INTEGER, track_uri VARCHAR, track_name VARCHAR,
    artist VARCHAR, artist_mbid VARCHAR, slot VARCHAR, score DOUBLE, propensity DOUBLE, reason VARCHAR
);
"""


def connect_recs(path: str | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(path or RECS_PATH)
    con.execute(RECS_SCHEMA)
    return con
