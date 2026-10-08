"""Seed weighting and candidate aggregation (pure logic) + a generator driver.

Seeds = artists you respond well to (label * sample weight, summed). Candidates = artists similar to
several seeds, minus every artist you already know. Aggregate score = sum over seeds of
seed_weight * (similarity / that seed's max similarity), so one prolific seed can't dominate.
"""
from collections import defaultdict

from radio.recommend.candidates import Candidate


def seed_weights(rows: list[dict], artist_of_uri: dict[str, str], top_n: int = 25) -> dict[str, float]:
    """Positive-net artists by summed label*weight, strongest top_n only."""
    tot = defaultdict(float)
    for r in rows:
        mbid = artist_of_uri.get(r["track_uri"])
        if mbid:
            tot[mbid] += r["label"] * r["weight"]
    pos = {m: w for m, w in tot.items() if w > 0}
    return dict(sorted(pos.items(), key=lambda kv: -kv[1])[:top_n])


def aggregate(per_seed: dict[str, list[Candidate]], seeds: dict[str, float], known: set[str]) -> list[dict]:
    """Rank unknown artists. Returns dicts: artist_mbid, name, score, seeds (list of seed mbids)."""
    acc = {}
    for seed, cands in per_seed.items():
        top = max((c.score for c in cands), default=0) or 1.0
        for c in cands:
            if c.artist_mbid in known:
                continue
            e = acc.setdefault(c.artist_mbid, {"artist_mbid": c.artist_mbid, "name": c.artist_name,
                                               "score": 0.0, "seeds": []})
            e["score"] += seeds.get(seed, 0.0) * (c.score / top)
            e["seeds"].append(seed)
    return sorted(acc.values(), key=lambda e: -e["score"])


def generate(rows, artist_of_uri, known, similar=None, top_n: int = 25) -> list[dict]:
    from radio.recommend.candidates.listenbrainz import similar_artists
    similar = similar or similar_artists
    seeds = seed_weights(rows, artist_of_uri, top_n)
    return aggregate({s: similar(s) for s in seeds}, seeds, known | set(seeds))


if __name__ == "__main__":
    from radio.db import connect_ids, connect_snapshot
    from radio.taste.pipeline import load_rows
    con = connect_snapshot()
    rows = load_rows(con)
    art = {u: m for u, m in connect_ids().execute("SELECT track_uri, artist_mbid FROM track_ids WHERE artist_mbid IS NOT NULL").fetchall()}
    out = generate(rows, art, known=set(art.values()))
    print(f"{len(rows)} labelled plays, {len(set(art.values()))} known artists")
    for e in out[:25]:
        print(f"{e['score']:.2f}  {e['name']}  (via {len(e['seeds'])} seeds)")
