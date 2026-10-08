import unittest
from datetime import datetime, timedelta

from radio.taste.pipeline import build_rows, mark_repeats

T0 = datetime(2026, 10, 7, 12, 0, 0)


def play(mins, uri="spotify:track:a", end="completed", ms=200_000, kind="user", ctx=None, ctype=None):
    return dict(started_at=T0 + timedelta(minutes=mins), track_uri=uri, end_reason=end, ms_played=ms,
                duration_ms=200_000, start_kind=kind, context_uri=ctx, context_type=ctype, incognito=False)


class PipelineTests(unittest.TestCase):
    def test_repeat_marks_earlier_play(self):
        ps = [play(0), play(10, "spotify:track:b"), play(20)]
        self.assertEqual(mark_repeats(ps), {(T0, "spotify:track:a")})

    def test_repeat_outside_window_ignored(self):
        self.assertEqual(mark_repeats([play(0), play(60 * 30)]), set())

    def test_save_after_play_upgrades_but_save_before_does_not(self):
        liked_later = build_rows([play(0, "spotify:track:s")], {"spotify:track:s": T0 + timedelta(hours=2)})[0]
        self.assertEqual(liked_later["label_name"], "strong_pos")
        self.assertFalse(liked_later["saved_asof_play"])
        liked_before = build_rows([play(0, "spotify:track:s")], {"spotify:track:s": T0 - timedelta(days=30)})[0]
        self.assertEqual(liked_before["label_name"], "weak_pos")      # familiarity, not evidence about this play
        self.assertTrue(liked_before["saved_asof_play"])
        too_late = build_rows([play(0, "spotify:track:s")], {"spotify:track:s": T0 + timedelta(days=30)})[0]
        self.assertEqual(too_late["label_name"], "weak_pos")

    def test_repeat_upgrades(self):
        rows = build_rows([play(0), play(5)], {})
        self.assertEqual(rows[0]["label_name"], "strong_pos")
        self.assertEqual(rows[1]["label_name"], "weak_pos")

    def test_weights_equal_and_drops(self):
        rows = build_rows([play(0, "spotify:track:x", kind="auto", ctx="spotify:playlist:p", ctype="playlist"),
                           play(5, "spotify:track:y", kind="user"),
                           play(9, "spotify:track:z", end="other", ms=50_000)], {})
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["weight"] for r in rows], [1.0, 1.0])     # autoplay counts as much as hand-picked
        self.assertFalse(rows[0]["intent"])
        self.assertTrue(rows[1]["intent"])                             # lone user-started track: a feature now


if __name__ == "__main__":
    unittest.main()
