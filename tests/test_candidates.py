import os
import tempfile
import unittest

from radio.recommend.candidates import Candidate
from radio.recommend.candidates import cache
from radio.recommend.candidates.artists import aggregate, seed_weights
from radio.recommend.candidates.listenbrainz import parse_similar, similar_artists
from radio.recommend.candidates import recordings as R


class CandidateTests(unittest.TestCase):
    def test_seed_weights_positive_only(self):
        rows = [dict(track_uri="t1", label=1.0, weight=1.5), dict(track_uri="t2", label=-1.0, weight=1.0),
                dict(track_uri="t3", label=0.4, weight=1.0), dict(track_uri="t4", label=0.4, weight=1.0)]
        a = {"t1": "A", "t2": "B", "t3": "C", "t4": "C"}
        self.assertEqual(seed_weights(rows, a), {"A": 1.5, "C": 0.8})

    def test_aggregate_ranks_shared_and_drops_known(self):
        per = {"A": [Candidate("X", "x", 10, "lb", "A"), Candidate("Y", "y", 5, "lb", "A"), Candidate("K", "k", 9, "lb", "A")],
               "C": [Candidate("Y", "y", 100, "lb", "C")]}
        out = aggregate(per, {"A": 1.0, "C": 1.0}, known={"K"})
        self.assertEqual([e["artist_mbid"] for e in out], ["Y", "X"])   # Y: .5 + 1.0 beats X: 1.0
        self.assertEqual(out[0]["seeds"], ["A", "C"])

    def test_parse_and_cache_avoids_second_fetch(self):
        rows = [{"artist_mbid": "S", "name": "self", "score": 9}, {"artist_mbid": "Z", "name": "z", "score": 3}]
        self.assertEqual([c.artist_mbid for c in parse_similar(rows, "S")], ["Z"])
        with tempfile.TemporaryDirectory() as d:
            cache.CACHE_DIR = d
            calls = []
            f = lambda m: calls.append(m) or rows
            similar_artists("S", fetch=f, sleep=lambda s: None)
            similar_artists("S", fetch=f, sleep=lambda s: None)
            self.assertEqual(len(calls), 1)


def nb(mbid, score, name=None, artist="x"):
    return {"recording_mbid": mbid, "score": score, "recording_name": name or mbid, "artist_credit_name": artist}


class RecordingTests(unittest.TestCase):
    def test_mutual_proximity_suppresses_hub(self):
        per = {"S": [nb("hub", 100), nb("fit", 90)]}
        own = {"hub": [nb(f"o{i}", 50) for i in range(10)],           # hub's own list does not contain S
               "fit": [nb("S", 80)] + [nb(f"p{i}", 10) for i in range(9)]}
        out = R.rank(per, {"S": 1.0}, own=own)
        self.assertEqual(out[0]["recording_mbid"], "fit")

    def test_breadth_damping_and_exclusion(self):
        per = {"A": [nb("c", 10), nb("x", 9)], "B": [nb("c", 10)], "K": [nb("known", 10)]}
        out = R.rank(per, {"A": 1.0, "B": 1.0, "K": 1.0}, exclude={"known"})
        self.assertNotIn("known", [e["recording_mbid"] for e in out])
        c = next(e for e in out if e["recording_mbid"] == "c")
        self.assertEqual(c["seeds"], ["A", "B"])
        self.assertAlmostEqual(c["score"], (R.MP_UNKNOWN ** 0.5 + R.MP_UNKNOWN ** 0.5 * 1.0) / 2 ** 0.5 * 1.0, places=6)

    def test_popularity_penalty_prefers_obscure(self):
        per = {"S": [nb("big", 10), nb("mid", 10), nb("small", 10)]}
        pop = {"big": 100000, "mid": 1000, "small": 10}
        out = R.rank(per, {"S": 1.0}, pop=pop, alpha=0.5)
        self.assertEqual(out[0]["recording_mbid"], "small")

    def test_popularity_gated_returns_empty(self):
        import urllib.error
        def deny(url, body):
            raise urllib.error.HTTPError(url, 401, "no token", {}, None)
        with tempfile.TemporaryDirectory() as d:
            cache.CACHE_DIR = d
            self.assertEqual(R.popularity(["a", "b"], post=deny), {})
            self.assertEqual(R.popularity(["a"], post=lambda u, b: [{"recording_mbid": "a", "total_user_count": 7}]), {"a": 7})

    def test_title_and_release_group_filters(self):
        ok = {"title": "Pink + White", "groups": [{"id": "g", "primary": "Album", "secondary": []}]}
        live_rg = {"title": "Song", "groups": [{"id": "g", "primary": "Album", "secondary": ["Live"]}]}
        remix = {"title": "Song (Remix)", "groups": [{"id": "g", "primary": "Single", "secondary": []}]}
        comp = {"title": "Song", "groups": [{"id": "g", "primary": "Album", "secondary": ["Compilation"]}]}
        self.assertTrue(R.acceptable(ok))
        self.assertFalse(any(R.acceptable(x) for x in (live_rg, remix, comp)))
        self.assertTrue(R.acceptable({"title": "Live Forever", "groups": ok["groups"]}))

    def test_build_splits_deepcuts_and_dedupes_release_groups(self):
        infos = {"r1": {"title": "A", "isrcs": ["I1"], "artists": [{"id": "new", "name": "n"}], "groups": [{"id": "g1", "primary": "Album", "secondary": []}]},
                 "r2": {"title": "B", "isrcs": ["I2"], "artists": [{"id": "new", "name": "n"}], "groups": [{"id": "g1", "primary": "Album", "secondary": []}]},
                 "r3": {"title": "C", "isrcs": ["I3"], "artists": [{"id": "liked", "name": "l"}], "groups": [{"id": "g3", "primary": "Album", "secondary": []}]}}
        per = {"S": [nb("r1", 10), nb("r2", 9), nb("r3", 8)]}
        out = R.build({"S": 1.0}, known_artists={"liked"}, known_recs=set(), known_uris=set(), sp=None,
                      neighbours_fn=lambda m: per.get(m, []), pop_fn=lambda ms: {}, mb_fn=lambda m: infos[m],
                      resolve=lambda sp, info: {"track_uri": "sp:" + info["isrcs"][0], "track_name": info["title"], "artist": "a"})
        self.assertEqual({o["recording_mbid"]: o["kind"] for o in out}, {"r1": "new", "r3": "deepcut"})   # r2 shares r1's album

    def test_deepcut_extra_popularity_penalty(self):
        mk = lambda t, a: {"title": t, "isrcs": [t], "artists": [{"id": a, "name": a}], "groups": [{"id": "g" + t, "primary": "Album", "secondary": []}]}
        infos = {"hit": mk("hit", "liked"), "cut": mk("cut", "liked"), "new": mk("new", "other")}
        per = {"S": [nb("hit", 10), nb("cut", 10), nb("new", 10)]}
        pop = {"hit": 100000, "cut": 100, "new": 1000}
        out = R.build({"S": 1.0}, {"liked"}, set(), set(), None, neighbours_fn=lambda m: per.get(m, []),
                      pop_fn=lambda ms: pop, mb_fn=lambda m: infos[m],
                      resolve=lambda sp, i: {"track_uri": "sp:" + i["title"], "track_name": i["title"], "artist": "a"})
        sc = {o["recording_mbid"]: o["score"] for o in out}
        self.assertGreater(sc["cut"], 3 * sc["hit"])          # the obscure deep cut far outranks the liked artist's hit


if __name__ == "__main__":
    unittest.main()
