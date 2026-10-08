import random
import unittest

import duckdb

from radio import db
from radio.recommend.candidates.picker import pick
from radio.recommend.playlist import combine, library_seeds


def cand(i, artist=None, score=None):
    return dict(track_uri=f"t{i}", artist=artist or f"a{i}", track_name=f"n{i}", score=score if score is not None else 100 - i, reason="r")


class PlaylistTests(unittest.TestCase):
    def test_slot_counts_and_uniqueness(self):
        out = pick([cand(i) for i in range(100)], n=30, rng=random.Random(3), runs=300)
        self.assertEqual(len(out), 30)
        self.assertEqual({o["slot"] for o in out}, {"confident", "explore", "wildcard"})
        self.assertEqual(sum(o["slot"] == "confident" for o in out), 21)   # no deepcut pool: its share goes to confident
        self.assertEqual(len({o["track_uri"] for o in out}), 30)
        self.assertEqual(sorted(o["position"] for o in out), list(range(30)))

    def test_confident_are_top_scored_and_propensity_valid(self):
        out = pick([cand(i) for i in range(100)], n=30, rng=random.Random(3), runs=300)
        top = {f"t{i}" for i in range(21)}
        self.assertEqual({o["track_uri"] for o in out if o["slot"] == "confident"}, top)
        self.assertTrue(all(0 < o["propensity"] <= 1 for o in out))
        self.assertTrue(all(o["propensity"] == 1.0 for o in out if o["slot"] == "confident"))
        self.assertTrue(all(o["propensity"] < 1 for o in out if o["slot"] == "wildcard"))

    def test_propensity_never_exceeds_one_and_matches_slot_mix(self):
        # steeply peaked scores: the old k*softmax formula gave > 1 here
        c = [cand(i, score=1000.0 if i < 8 else 1.0) for i in range(60)]
        out = pick(c, n=30, rng=random.Random(5), runs=500)
        self.assertTrue(all(0 < o["propensity"] <= 1 for o in out))

    def test_inclusion_probabilities_sum_to_playlist_length(self):
        from collections import Counter
        from radio.recommend.candidates.picker import _generate
        c = [cand(i, score=50.0 - i) for i in range(70)]
        r, cnt = random.Random(9), Counter()
        for _ in range(400):
            cnt.update(o["track_uri"] for o in _generate(c, 30, 0.7, 0.2, 0.0, r, 2, 1.0))
        self.assertAlmostEqual(sum(cnt.values()) / 400, 30, delta=0.01)    # sum of inclusion probs = n

    def test_deepcut_slot_is_capped_and_labelled(self):
        c = [cand(i) for i in range(80)] + [{**cand(100 + i, score=50 - i), "kind": "deepcut"} for i in range(20)]
        out = pick(c, n=30, rng=random.Random(2), runs=200)
        deep = [o for o in out if o["slot"] == "deepcut"]
        self.assertEqual(len(deep), 6)                                      # 20% of 30
        self.assertTrue(all(o["track_uri"].startswith("t1") for o in deep))
        self.assertEqual(len(out), 30)
        self.assertTrue(all(o["slot"] == "deepcut" for o in out if o.get("kind") == "deepcut"))

    def test_max_per_artist_and_small_pool(self):
        c = [cand(i, artist="same") for i in range(10)]
        self.assertEqual(len(pick(c, n=30, rng=random.Random(1), runs=50)), 2)      # capped, pool exhausted: no crash
        self.assertEqual(pick([], n=30), [])

    def test_position_independent_of_score(self):
        pos = [next(o["position"] for o in pick([cand(i) for i in range(60)], n=30, rng=random.Random(s), runs=20) if o["track_uri"] == "t0")
               for s in range(40)]
        self.assertGreater(len(set(pos)), 10)                              # the best track lands all over the list

    def test_library_seeds(self):
        ev, ids = duckdb.connect(":memory:"), duckdb.connect(":memory:")
        ev.execute(db.SCHEMA); ids.execute(db.IDS_SCHEMA)
        ids.execute("INSERT INTO track_ids (track_uri, artist_mbid) VALUES ('s:a','A'), ('s:b','A'), ('s:c','B')")
        ids.execute("INSERT INTO basis_tracks VALUES ('liked','s:a',now()), ('liked','s:b',now()), ('playlist:Chill','s:b',now())")
        ev.execute("INSERT INTO top_items VALUES ('track','short_term',1,'s:c','c',now()), ('artist','short_term',1,'x','x',now())")
        from datetime import datetime
        w = library_seeds(ids, ev, now=datetime.now())
        self.assertAlmostEqual(w["A"], 2 ** 0.5, places=3)           # two tracks (s:b is in two sources but counts once) -> sqrt(2)
        self.assertAlmostEqual(w["B"], 0.25)                         # top track only: minor boost
        self.assertGreater(w["A"], w["B"])
        self.assertEqual(list(combine({"A": 1.0}, {"A": 1.0, "B": 3.0}, top_n=1)), ["B"])

    def test_old_saves_decay_gently(self):
        from datetime import datetime, timedelta
        ev, ids = duckdb.connect(":memory:"), duckdb.connect(":memory:")
        ev.execute(db.SCHEMA); ids.execute(db.IDS_SCHEMA)
        ids.execute("INSERT INTO track_ids (track_uri, artist_mbid) VALUES ('s:a','A'), ('s:b','B')")
        now = datetime(2026, 10, 8)
        ids.execute("INSERT INTO basis_tracks VALUES ('liked','s:a',?), ('liked','s:b',?)", [now, now - timedelta(days=365)])
        w = library_seeds(ids, ev, now=now)
        self.assertAlmostEqual(w["B"] / w["A"], 0.5 ** 0.5, places=3)   # one half-life, then sqrt


if __name__ == "__main__":
    unittest.main()
