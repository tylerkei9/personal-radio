"""Identity resolver: Spotify URI -> ISRC (Spotify `tracks`) -> MusicBrainz recording/artist MBIDs.

Results are cached in `track_ids`. Only minimal metadata is stored. MusicBrainz asks for <= 1 req/s
and a descriptive User-Agent (set RADIO_CONTACT to an email or URL).
"""
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger("ids")
MB_URL = "https://musicbrainz.org/ws/2/recording"
MB_INTERVAL_S = 1.1
UA = f"personal-radio/0.1 ({os.environ.get('RADIO_CONTACT', 'local-use')})"


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def norm_isrc(isrc: str | None) -> str | None:
    """Spotify sometimes returns hyphenated ISRCs (QZ-L38-24-68720); every lookup wants the bare 12 chars."""
    return isrc.replace("-", "").strip().upper() if isrc else None


def uri_to_id(uri: str) -> str | None:
    parts = uri.split(":")
    return parts[2] if len(parts) == 3 and parts[1] == "track" else None


def parse_mb_recordings(data: dict) -> tuple[str | None, str | None]:
    """First recording hit -> (recording_mbid, first artist mbid); (None, None) on a miss."""
    for rec in data.get("recordings") or []:
        credit = rec.get("artist-credit") or []
        artist = (credit[0].get("artist") or {}).get("id") if credit else None
        return rec.get("id"), artist
    return None, None


def mb_fetch(isrc: str) -> dict:
    q = urllib.parse.urlencode({"query": f"isrc:{isrc}", "fmt": "json", "limit": 1})
    req = urllib.request.Request(f"{MB_URL}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def seed_tracks(ids_con, ev_con) -> int:
    """Register every track you played, saved, or have in top items. ISRCs the poller already
    captured (plays) or an earlier identity cache (events DB `track_ids`) are carried over."""
    rows = ev_con.execute("""
        SELECT track_uri, max(replace(isrc, '-', '')) FROM plays GROUP BY track_uri
        UNION ALL SELECT track_uri, NULL FROM saves
        UNION ALL SELECT uri, NULL FROM top_items WHERE kind = 'track'""").fetchall()
    rows += ids_con.execute("SELECT DISTINCT track_uri, NULL FROM basis_tracks").fetchall()
    try:   # one-time carry-over from when the cache lived in the events DB
        rows += ev_con.execute("SELECT track_uri, replace(isrc, '-', '') FROM track_ids WHERE isrc IS NOT NULL").fetchall()
    except Exception:
        pass
    best = {}
    for uri, isrc in rows:
        best[uri] = best.get(uri) or isrc
    ids_con.executemany(
        "INSERT INTO track_ids (track_uri, isrc) VALUES (?, ?) "
        "ON CONFLICT (track_uri) DO UPDATE SET isrc = coalesce(track_ids.isrc, excluded.isrc)", list(best.items()))
    return ids_con.execute("SELECT count(*) FROM track_ids").fetchone()[0]


def backfill_isrc(sp, con, limit: int = 200, pause_s: float = 0.3, sleep=time.sleep) -> int:
    """Fetch missing ISRCs from Spotify one track at a time (the batch `tracks` endpoint is 403 for
    Development Mode apps). Failed lookups are left unchecked so they retry next run."""
    uris = [r[0] for r in con.execute(
        "SELECT track_uri FROM track_ids WHERE isrc IS NULL AND isrc_checked_at IS NULL LIMIT ?", [limit]).fetchall()]
    found = 0
    for u in uris:
        tid = uri_to_id(u)
        if not tid:
            continue
        try:
            isrc = norm_isrc((sp.track(tid).get("external_ids") or {}).get("isrc"))
        except Exception as e:
            log.warning("isrc lookup failed for %s: %s", u, e)
            if getattr(e, "http_status", None) == 429:    # shared quota with the live tracker: stop, retry next run
                break
            continue
        con.execute("UPDATE track_ids SET isrc = ?, isrc_checked_at = ? WHERE track_uri = ?", [isrc, _now(), u])
        found += bool(isrc)
        sleep(pause_s)
    return found


def resolve_mbids(con, fetch=mb_fetch, limit: int = 100, sleep=time.sleep, max_fail_streak: int = 5) -> int:
    """Look up MusicBrainz IDs by ISRC, rate-limited. Failed rows stay unchecked and retry next run.
    Backs off exponentially on consecutive failures (MusicBrainz 503s when throttling) and gives up after a streak."""
    rows = con.execute("SELECT track_uri, isrc FROM track_ids WHERE isrc IS NOT NULL AND mb_checked_at IS NULL "
                       "LIMIT ?", [limit]).fetchall()
    hits = fails = 0
    for uri, isrc in rows:
        try:
            rec, art = parse_mb_recordings(fetch(isrc))
        except Exception as e:
            fails += 1
            log.warning("musicbrainz lookup failed for %s: %s", isrc, e)
            if fails >= max_fail_streak:
                log.warning("musicbrainz: %d failures in a row, stopping; rerun later", fails)
                break
            sleep(MB_INTERVAL_S * 2 ** fails)       # 2.2s, 4.4s, 8.8s, ...
            continue
        fails = 0
        con.execute("UPDATE track_ids SET recording_mbid = ?, artist_mbid = ?, mb_checked_at = ? WHERE track_uri = ?",
                    [rec, art, _now(), uri])
        hits += bool(rec)
        sleep(MB_INTERVAL_S)
    return hits


if __name__ == "__main__":
    from radio.db import connect_ids, connect_snapshot
    from radio.collect.poller import build_client
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    con = connect_ids()
    print("tracks:", seed_tracks(con, connect_snapshot()))
    print("isrc found:", backfill_isrc(build_client(timeout=30), con))
    print("mbids found:", resolve_mbids(con))
    print(con.execute("SELECT count(*), count(isrc), count(recording_mbid), count(mb_checked_at) FROM track_ids").fetchone(),
          "(tracks, isrc, mbid, mb_checked)")
