"""Build and (optionally) write the "Weekly Auto" playlist. Dry run by default.

Usage: python -m radio playlist [--write] [--n 30] [--seed 1]
Pipeline: seed recordings (taste basis, weighted per artist) -> ListenBrainz similar-recordings (mutual proximity,
breadth damping, popularity penalty) -> MusicBrainz filter (no remixes/lives/compilations, one per release group) ->
Spotify `isrc:` lookup -> picker (confident / deepcut / explore / wildcard) -> log -> write.
Candidates by artists you already like become the capped "deepcut" slot. Falls back to the old artist-level path
(`--artist-level`) for comparison.
"""
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import spotipy

from radio import paths
from radio.recommend.candidates.artists import aggregate, seed_weights
from radio.recommend.candidates.cache import cached
from radio.recommend.candidates.listenbrainz import similar_artists
from radio.taste.basis import sync_basis
from radio.recommend.candidates.picker import pick

log = logging.getLogger("playlist")
STATE = paths.PLAYLIST_STATE
NAME = "Personal Radio - Weekly Auto"
TRACK_DECAY = [1.0, 0.7, 0.5]       # a candidate artist's 1st, 2nd, 3rd track
SPOTIFY_CACHE_TTL_S = 86400         # Spotify content is cached for a day only (developer terms: "strictly necessary")


SAVE_HALF_LIFE_DAYS = 365.0   # liked songs are long-standing taste: gentle recency only
TOP_TRACK_SCALE = 0.25        # top tracks / recent plays are minor boosts next to the liked library
PLAY_SCALE = 0.5


def library_seeds(ids_con, ev_con=None, now: datetime | None = None) -> dict[str, float]:
    """The taste basis (liked songs + merged playlists, deduplicated) drives the seeds. Per artist:
    sqrt(sum of decayed track weights), so one heavily-represented artist cannot swamp the rest. Top tracks
    (short 1.0 / medium 0.7 / long 0.5 x TOP_TRACK_SCALE) add a small boost."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    art = dict(ids_con.execute("SELECT track_uri, artist_mbid FROM track_ids WHERE artist_mbid IS NOT NULL").fetchall())
    liked = defaultdict(float)
    for uri, ts in ids_con.execute("SELECT track_uri, max(added_at) FROM basis_tracks GROUP BY track_uri").fetchall():
        if uri in art:
            age = (now - ts).total_seconds() / 86400 if ts else 0.0
            liked[art[uri]] += 0.5 ** (age / SAVE_HALF_LIFE_DAYS)
    w = {m: v ** 0.5 for m, v in liked.items()}
    if ev_con is not None:
        scale = {"short_term": 1.0, "medium_term": 0.7, "long_term": 0.5}
        for uri, rng_ in ev_con.execute("SELECT uri, time_range FROM top_items WHERE kind='track'").fetchall():
            if uri in art:
                w[art[uri]] = w.get(art[uri], 0.0) + TOP_TRACK_SCALE * scale.get(rng_, 0.5)
    return w


def combine(*weights: dict[str, float], top_n: int = 40) -> dict[str, float]:
    tot = defaultdict(float)
    for d in weights:
        for k, v in d.items():
            tot[k] += v
    return dict(sorted(tot.items(), key=lambda kv: -kv[1])[:top_n])


def artist_name(mbid: str, fetch) -> str:
    try:
        return cached(f"mb-artist:{mbid}", lambda: fetch(mbid), ttl_s=30 * 86400).get("name", mbid[:8])
    except Exception:
        return mbid[:8]


def tracks_for_artist(sp, name: str, n: int = 3, sleep=time.sleep) -> list[dict]:
    """Top-ish tracks by an artist via Spotify search (limit 10 max). Exact artist-name match only."""
    def go():
        sleep(0.3)
        items = sp.search(q=f'artist:"{name}"', type="track", limit=10)["tracks"]["items"]
        return [{"track_uri": t["uri"], "track_name": t["name"], "artist": t["artists"][0]["name"],
                 "all_artists": [a["name"].lower() for a in t["artists"]]} for t in items]
    items = cached(f"sp-artist-tracks:{name.lower()}", go, ttl_s=SPOTIFY_CACHE_TTL_S)
    seen, out = set(), []
    for t in items:
        key = t["track_name"].lower()
        if name.lower() in t["all_artists"][:1] and key not in seen:     # primary artist only; dedupe re-releases
            seen.add(key); out.append(t)
    return out[:n]


def recording_seeds(ids_con, artist_w: dict[str, float]) -> dict[str, float]:
    """Seed weight per recording: its artist's seed weight split across that artist's basis tracks, so the artist
    total (already sqrt-damped) is preserved and a prolific artist does not get more seed slots."""
    rows = ids_con.execute("SELECT DISTINCT t.recording_mbid, t.artist_mbid FROM basis_tracks b JOIN track_ids t USING (track_uri) "
                           "WHERE t.recording_mbid IS NOT NULL AND t.artist_mbid IS NOT NULL").fetchall()
    n = defaultdict(int)
    for _, a in rows:
        n[a] += 1
    return {r: artist_w[a] / n[a] for r, a in rows if a in artist_w}


def build_candidates(ranked_artists, sp, known_uris: set[str], names: dict[str, str], limit_artists: int = 80) -> list[dict]:
    cands = []
    for a in ranked_artists[:limit_artists]:
        try:
            tracks = tracks_for_artist(sp, a["name"])
        except Exception as e:
            log.warning("track lookup failed for %s: %s", a["name"], e)
            continue
        why = ", ".join(names.get(s, s[:8]) for s in a["seeds"][:3]) + (f" +{len(a['seeds']) - 3}" if len(a["seeds"]) > 3 else "")
        for rank, t in enumerate(tracks):
            if t["track_uri"] in known_uris:
                continue
            cands.append({**t, "artist_mbid": a["artist_mbid"], "score": a["score"] * TRACK_DECAY[min(rank, 2)],
                          "reason": f"similar to {why}; track #{rank + 1} for this artist"})
    return cands


def _create(sp) -> str:
    pid = sp._post("me/playlists", payload={"name": NAME, "public": False,
                                            "description": "Auto-generated by Personal Radio. Rewritten on each run."})["id"]
    json.dump({"playlist_id": pid}, open(STATE, "w"))
    return pid


def write_playlist(sp, picks: list[dict]) -> str:
    """Create-or-replace the playlist, then verify it exists and holds every track (the API can accept a write
    without keeping it). Recreates the playlist if the saved id is gone (e.g. deleted in the app)."""
    uris = [p["track_uri"] for p in sorted(picks, key=lambda p: p["position"])]
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    pid = state.get("playlist_id") or _create(sp)
    try:
        sp._put(f"playlists/{pid}/items", payload={"uris": uris})
    except spotipy.SpotifyException as e:
        if e.http_status != 404:
            raise
        log.warning("playlist %s is gone (404); creating a new one", pid)
        pid = _create(sp)
        sp._put(f"playlists/{pid}/items", payload={"uris": uris})
    got = sp._get(f"playlists/{pid}/items", limit=1).get("total")
    mine = [p["id"] for p in sp._get("me/playlists", limit=50)["items"]]
    if got != len(uris) or pid not in mine:
        raise RuntimeError(f"write not confirmed: playlist has {got} items (expected {len(uris)}), listed in account: {pid in mine}")
    return pid


def main(argv):
    from radio.recommend.candidates.artists import generate  # noqa: F401  (kept importable)
    from radio.db import connect_ids, connect_recs, connect_snapshot
    from radio.taste.ids import UA
    from radio.taste.pipeline import load_rows
    from radio.collect.poller import build_client
    import urllib.request

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 30
    rng = random.Random(int(argv[argv.index("--seed") + 1])) if "--seed" in argv else random.Random()
    ev, ids = connect_snapshot(), connect_ids()
    sp = build_client(timeout=30)
    print("taste basis:", sync_basis(sp, ids, ev))
    missing = ids.execute("SELECT count(*) FROM basis_tracks b LEFT JOIN track_ids t USING (track_uri) "
                          "WHERE t.artist_mbid IS NULL").fetchone()[0]
    if missing:
        from radio.taste.ids import backfill_isrc, resolve_mbids, seed_tracks
        seed_tracks(ids, ev); backfill_isrc(sp, ids); resolve_mbids(ids)
        print(f"resolved identities for new basis tracks ({missing} lacked an artist MBID before)")
    art = dict(ids.execute("SELECT track_uri, artist_mbid FROM track_ids WHERE artist_mbid IS NOT NULL").fetchall())
    plays = {m: PLAY_SCALE * v for m, v in seed_weights(load_rows(ev), art, top_n=100).items()}
    seeds = combine(library_seeds(ids, ev), plays)
    known_artists = set(art.values())
    mb_fetch = lambda m: json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://musicbrainz.org/ws/2/artist/{m}?fmt=json", headers={"User-Agent": UA}), timeout=20))
    names = {s: artist_name(s, mb_fetch) for s in list(seeds)[:15]}
    known_uris = {r[0] for r in ids.execute('SELECT track_uri FROM basis_tracks').fetchall()} | set(art) | {r[0] for r in ev.execute("SELECT track_uri FROM plays").fetchall()} \
        | {r[0] for r in ev.execute("SELECT track_uri FROM saves").fetchall()}
    recs = connect_recs()
    known_uris |= {r[0] for r in recs.execute("SELECT track_uri FROM picks").fetchall()}   # never repeat a recommendation
    if "--artist-level" in argv:
        per_seed = {s: similar_artists(s) for s in seeds}
        ranked = aggregate(per_seed, seeds, known_artists | set(seeds))
        cands = build_candidates(ranked, sp, known_uris, names)
        print(f"{len(seeds)} seeds, {len(ranked)} candidate artists, {len(cands)} candidate tracks")
    else:
        from radio.recommend.candidates import recordings
        known_recs = set(r[0] for r in ids.execute("SELECT recording_mbid FROM track_ids WHERE recording_mbid IS NOT NULL").fetchall())
        cands = recordings.build(recording_seeds(ids, seeds), known_artists, known_recs, known_uris, sp)
        print(f"{len(seeds)} artist seeds -> {len(cands)} candidate tracks "
              f"({sum(c['kind'] == 'deepcut' for c in cands)} deep cuts from artists you like)")
    picks = pick(cands, n=n, rng=rng)
    print(f"{len(picks)} picks")
    for p in sorted(picks, key=lambda p: p["position"]):
        print(f"{p['position']:2d} [{p['slot']:9s} p={p['propensity']:.2f}] {p['artist']} - {p['track_name']}   ({p['reason']})")
    if "--write" in argv:
        pid = write_playlist(sp, picks)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        recs.executemany("INSERT INTO picks VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            (pid, now, p["position"], p["track_uri"], p["track_name"], p["artist"], p.get("artist_mbid"),
             p["slot"], p["score"], p["propensity"], p["reason"]) for p in picks])
        print(f"wrote {len(picks)} tracks to playlist {pid}; logged to radio_recs.duckdb")
    else:
        print("dry run: nothing written (use --write)")


if __name__ == "__main__":
    main(sys.argv[1:])
