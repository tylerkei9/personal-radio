import random
import unittest
from datetime import datetime, timedelta

from radio.evalkit.baselines import decayed_replay, item_knn, most_pop, sessions
from radio.evalkit.metrics import ndcg_at_k, paired_bootstrap, recall_at_k
from radio.evalkit.run import evaluate
from radio.evalkit.splits import rolling_origin

T0 = datetime(2026, 1, 1, 12)


def row(day, track, label=1.0, minute=0):
    return dict(started_at=T0 + timedelta(days=day, minutes=minute), track_uri=track, label=label, weight=1.0)


class EvalKitTests(unittest.TestCase):
    def test_splits_never_leak_future_or_gap(self):
        rows = [row(d, f"t{d % 3}", minute=m) for d in range(10) for m in (0, 5)]
        folds = list(rolling_origin(rows, min_train=2))
        self.assertTrue(folds)
        for start, train, test in folds:
            self.assertTrue(all(r["started_at"] < start - timedelta(hours=1) for r in train))
            self.assertTrue(all(r["started_at"] >= start for r in test))

    def test_decay_prefers_recent_over_old(self):
        train = [row(0, "old"), row(0, "old"), row(30, "new")]
        s = decayed_replay(train, T0 + timedelta(days=31), half_life_days=7)
        self.assertGreater(s("new"), s("old"))
        self.assertGreater(most_pop(train)("old"), most_pop(train)("new"))     # raw popularity prefers old

    def test_negatives_never_score(self):
        self.assertEqual(decayed_replay([row(0, "x", label=-1.0)], T0 + timedelta(days=1))("x"), 0.0)

    def test_item_knn_uses_cooccurrence(self):
        train = [row(0, "a", minute=0), row(0, "b", minute=3),           # session 1: a with b
                 row(1, "c", minute=0), row(1, "d", minute=3),           # session 2: c with d
                 row(5, "a", minute=0)]                                  # recent positive: a
        s = item_knn(train, T0 + timedelta(days=6))
        self.assertGreater(s("b"), s("d"))
        self.assertEqual(len(sessions(train)), 3)

    def test_metrics_and_bootstrap(self):
        self.assertAlmostEqual(ndcg_at_k(["a", "b"], {"a"}), 1.0)
        self.assertAlmostEqual(recall_at_k(["x", "y", "a"], {"a", "z"}, k=3), 0.5)
        diff, ci, p = paired_bootstrap([0.5] * 10, [0.1] * 10)
        self.assertGreater(diff, 0); self.assertGreater(ci[0], 0); self.assertEqual(p, 1.0)

    def test_replay_beats_random_on_repetitive_listener(self):
        rng = random.Random(1)
        favs = [f"fav{i}" for i in range(5)]
        rows = [row(d, rng.choice(favs), minute=m * 4) for d in range(20) for m in range(6)]
        rows += [row(d, f"noise{d}{m}", label=-0.6, minute=40 + m) for d in range(20) for m in range(3)]
        res = evaluate(rows, min_train=10)
        replay = sum(x[0] for x in res["decayed_replay"]) / len(res["decayed_replay"])
        self.assertGreater(replay, 0.5)


if __name__ == "__main__":
    unittest.main()
