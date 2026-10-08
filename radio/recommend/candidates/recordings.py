"""Recording-level candidates from ListenBrainz Labs `similar-recordings` (public, no token), with hub corrections.

Pipeline (pure scoring in `rank`; network helpers are injectable for tests):
  seed recordings -> neighbours per seed -> score = sum_s w_s * sim_norm * mutual_proximity, / sqrt(#seeds listing it),
  * popularity^-alpha  ->  MusicBrainz lookup (artist, ISRCs, release-group types) -> drop remixes/lives/compilations,
  one per release group -> Spotify `isrc:` search for a URI.
Coverage is partial (about a third of seeds have neighbours), so a missing list is "unknown", not "unrelated".
"""
import hashlib
import json
import logging
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict

from radio.recommend.candidates.cache import cached
from radio.taste.ids import MB_INTERVAL_S, UA, norm_isrc

log = logging.getLogger("candidates.recordings")
SIM_URL = "https://labs.api.listenbrainz.org/similar-recordings/json"
POP_URL = "https://api.listenbrainz.org/1/popularity/recording"
MB_REC = "https://musicbrainz.org/ws/2/recording/{}?inc=isrcs+releases+release-groups+artist-credits&fmt=json"
ALGO = "session_based_days_9000_session_300_contribution_5_threshold_15_limit_50_skip_30"
MP_UNKNOWN = 0.5      # candidate's own neighbour list unavailable: neutral
MP_ABSENT = 0.1       # list available but the seed is not in it: probably a hub that everything points at
POP_ALPHA = 0.3
DEEP_EXTRA_ALPHA = 0.5   # deep cuts get a second, stronger popularity penalty: a liked artist's biggest hit is not a deep cut
SECONDARY_BAD = {"Live", "Remix", "Compilation", "DJ-mix", "Demo", "Mixtape/Street", "Soundtrack", "Spokenword"}
# Qualifiers only count inside (...), [...] or after " - ": "Live Forever" is a song, "Song (Live)" is not.
TITLE_BAD = re.compile(r"karaoke|sped up|slowed|nightcore|"
                       r"[(\[]\s*[^)\]]*\b(remix|live|acoustic|instrumental|demo|edit|extended|cover|reprise|version|remaster\w*|mix)\b|"
                       r"\s-\s[^-]*\b(remix|live|acoustic|instrumental|demo|edit|extended|version|remaster\w*|mix)\b", re.I)


def _post(url: str, body, timeout=30):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_neighbours(mbid: str) -> list[dict]:
    return _post(SIM_URL, [{"recording_mbids": [mbid], "algorithm": ALGO}])


def neighbours(mbid: str, fetch=fetch_neighbours, sleep=time.sleep) -> list[dict]:
    """Recording neighbours of `mbid`, best first. Cached 7 days; [] on failure."""
    fetched = []

    def go():
        fetched.append(1)
        return fetch(mbid)
    try:
        rows = cached(f"lb-simrec:{mbid}", go)
    except Exception as e:
        log.warning("similar-recordings failed for %s: %s", mbid, e)
        return []
    if fetched:
        sleep(0.6)
    return sorted((r for r in rows if r.get("recording_mbid") and r["recording_mbid"] != mbid),
                  key=lambda r: -float(r.get("score") or 0))


def popularity(mbids: list[str], post=_post) -> dict[str, int]:
    """recording_mbid -> total_user_count. The endpoint is gated intermittently (401): then return {} and score
    without a popularity penalty rather than failing."""
    out, todo = {}, list(mbids)
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        try:
            rows = cached("lb-pop-batch:" + hashlib.sha1(" ".join(chunk).encode()).hexdigest(), lambda: post(POP_URL, {"recording_mbids": chunk}),
                          ttl_s=86400)
        except urllib.error.HTTPError as e:
            log.warning("popularity unavailable (HTTP %s): scoring without a popularity penalty", e.code)
            return out
        except Exception as e:
            log.warning("popularity failed: %s", e)
            return out
        out.update({r["recording_mbid"]: int(r.get("total_user_count") or 0) for r in rows})
    return out


def rank(per_seed: dict[str, list[dict]], seed_w: dict[str, float], own: dict[str, list[dict]] | None = None,
         pop: dict[str, int] | None = None, alpha: float = POP_ALPHA, exclude: set[str] = frozenset()) -> list[dict]:
    """Score candidate recordings. per_seed: seed -> neighbours (best first). own: candidate -> its own neighbours
    (for mutual proximity). pop: recording -> listener count. Returns dicts sorted by score, best first."""
    own, pop = own or {}, pop or {}
    acc = {}
    for seed, nbrs in per_seed.items():
        if not nbrs or seed_w.get(seed, 0) <= 0:
            continue
        top = max(float(n.get("score") or 0) for n in nbrs) or 1.0
        for rank_, n in enumerate(nbrs):
            c = n["recording_mbid"]
            if c in exclude or c == seed:
                continue
            fwd = 1 - rank_ / len(nbrs)                        # empirical-rank mutual proximity, seed -> candidate
            if c in own and own[c]:
                back = next((1 - j / len(own[c]) for j, m in enumerate(own[c]) if m["recording_mbid"] == seed), MP_ABSENT)
            else:
                back = MP_UNKNOWN
            e = acc.setdefault(c, {"recording_mbid": c, "name": n.get("recording_name") or "",
                                   "artist": n.get("artist_credit_name") or "", "release_mbid": n.get("release_mbid"),
                                   "raw": 0.0, "seeds": []})
            e["raw"] += seed_w[seed] * (float(n.get("score") or 0) / top) * (fwd * back) ** 0.5
            e["seeds"].append(seed)
    known_pop = sorted(v for v in pop.values() if v > 0)
    med = known_pop[len(known_pop) // 2] if known_pop else None
    out = []
    for e in acc.values():
        s = e["raw"] / len(e["seeds"]) ** 0.5                  # breadth damping: listed by many seeds != better fit
        p = pop.get(e["recording_mbid"])
        rel = p / med if med and p else None                    # popularity relative to the candidate median
        if rel:
            s *= min(3.0, max(0.3, rel ** -alpha))
        out.append({**e, "score": s, "pop": p, "pop_rel": rel})
    return sorted(out, key=lambda e: -e["score"])


def fetch_mb(mbid: str) -> dict:
    req = urllib.request.Request(MB_REC.format(mbid), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def mb_info(mbid: str, fetch=fetch_mb, sleep=time.sleep) -> dict | None:
    """Minimal MusicBrainz facts about a recording (cached 30 days). None if MusicBrainz is unreachable."""
    fetched = []

    def go():
        fetched.append(1)
        d = fetch(mbid)
        return {"title": d.get("title", ""), "isrcs": d.get("isrcs") or [],
                "artists": [{"id": c["artist"]["id"], "name": c.get("name") or c["artist"].get("name", "")}
                            for c in d.get("artist-credit") or [] if isinstance(c, dict) and "artist" in c],
                "groups": [{"id": r["release-group"]["id"], "primary": r["release-group"].get("primary-type"),
                            "secondary": r["release-group"].get("secondary-types") or []}
                           for r in d.get("releases") or [] if r.get("release-group")]}
    try:
        info = cached(f"mb-rec:{mbid}", go, ttl_s=30 * 86400)
    except Exception as e:
        log.warning("musicbrainz lookup failed for %s: %s", mbid, e)
        sleep(MB_INTERVAL_S * 3)
        return None
    if fetched:
        sleep(MB_INTERVAL_S)
    return info


def release_group(info: dict) -> str | None:
    """Prefer an Album/EP/Single group with no bad secondary type; None if the recording only lives on bad releases."""
    for g in info["groups"]:
        if g["primary"] in ("Album", "EP", "Single") and not (set(g["secondary"]) & SECONDARY_BAD):
            return g["id"]
    return None


def acceptable(info: dict) -> bool:
    return not TITLE_BAD.search(info["title"]) and release_group(info) is not None


def spotify_track(sp, info: dict, sleep=time.sleep) -> dict | None:
    """Resolve a recording to a Spotify track by exact ISRC (cached one day: Spotify content is kept short-lived)."""
    for isrc in map(norm_isrc, info["isrcs"]):
        def go(isrc=isrc):
            sleep(0.3)
            items = sp.search(q=f"isrc:{isrc}", type="track", limit=1)["tracks"]["items"]
            return [{"track_uri": t["uri"], "track_name": t["name"], "artist": t["artists"][0]["name"]} for t in items]
        try:
            hit = cached(f"sp-isrc:{isrc}", go, ttl_s=86400)
        except Exception as e:
            log.warning("isrc search failed for %s: %s", isrc, e)
            continue
        if hit:
            return hit[0]
    return None


def build(seed_w: dict[str, float], known_artists: set[str], known_recs: set[str], known_uris: set[str], sp,
          pool: int = 120, neighbours_fn=neighbours, pop_fn=popularity, mb_fn=mb_info, resolve=spotify_track) -> list[dict]:
    """Full recording-level candidate build. Returns candidate dicts (for `picker.pick`): kind is 'deepcut' when the
    artist is one you already like, otherwise a normal new-artist candidate."""
    per_seed = {s: neighbours_fn(s) for s in seed_w}
    covered = sum(bool(v) for v in per_seed.values())
    log.info("%d/%d seed recordings have neighbours", covered, len(seed_w))
    first = rank(per_seed, seed_w, exclude=set(known_recs))
    head = [e["recording_mbid"] for e in first[:pool]]
    own = {c: neighbours_fn(c) for c in head}                  # their own lists, for mutual proximity
    pop = pop_fn(head)
    ranked = rank(per_seed, seed_w, own=own, pop=pop, exclude=set(known_recs))
    out, seen_groups = [], set()
    for e in ranked[:pool]:
        info = mb_fn(e["recording_mbid"])
        if not info or not acceptable(info):
            continue
        g = release_group(info)
        if g in seen_groups:                                   # one pick per release group (MMR-lite)
            continue
        arts = {a["id"] for a in info["artists"]}
        deep = bool(arts & known_artists)
        t = resolve(sp, info)
        if not t or t["track_uri"] in known_uris:
            continue
        seen_groups.add(g)
        score = e["score"]
        if deep and e.get("pop_rel"):
            score *= min(3.0, max(0.2, e["pop_rel"] ** -DEEP_EXTRA_ALPHA))
        why = f"co-listened with {len(e['seeds'])} of your tracks"
        out.append({**t, "artist_mbid": info["artists"][0]["id"] if info["artists"] else None, "score": score,
                    "kind": "deepcut" if deep else "new", "recording_mbid": e["recording_mbid"],
                    "reason": ("deep cut from an artist you like; " if deep else "") + why})
    return out
