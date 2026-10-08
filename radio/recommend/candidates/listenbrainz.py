"""ListenBrainz Labs similar-artists (public, no token). Cached; polite default rate."""
import json
import logging
import time
import urllib.parse
import urllib.request

from radio.recommend.candidates import Candidate
from radio.recommend.candidates.cache import cached
from radio.taste.ids import UA

log = logging.getLogger("candidates.listenbrainz")
URL = "https://labs.api.listenbrainz.org/similar-artists/json"
ALGO = "session_based_days_9000_session_300_contribution_5_threshold_15_limit_50_skip_30"
MIN_INTERVAL_S = 0.5


def fetch_similar(mbid: str) -> list[dict]:
    q = urllib.parse.urlencode({"artist_mbids": mbid, "algorithm": ALGO})
    req = urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def parse_similar(rows: list[dict], seed_mbid: str) -> list[Candidate]:
    return [Candidate(r["artist_mbid"], r.get("name") or "", float(r.get("score") or 0), "listenbrainz", seed_mbid)
            for r in rows if r.get("artist_mbid") and r["artist_mbid"] != seed_mbid]


def similar_artists(mbid: str, fetch=fetch_similar, sleep=time.sleep) -> list[Candidate]:
    fetched = []

    def _go():
        fetched.append(1)
        return fetch(mbid)
    try:
        rows = cached(f"lb-similar:{mbid}", _go)
    except Exception as e:
        log.warning("similar-artists failed for %s: %s", mbid, e)
        return []
    if fetched:
        sleep(MIN_INTERVAL_S)       # only throttle real network calls
    return parse_similar(rows, mbid)
