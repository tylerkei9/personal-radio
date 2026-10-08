import unittest
from datetime import datetime, timedelta

from radio.collect import poller
from radio.collect.sync import missing_recent
from radio.collect.tracker import Snapshot

T0 = datetime(2026, 10, 8, 12, 0, 0)


def snap(track="t", playing=True, progress=30_000, dur=200_000):
    return Snapshot(ts=T0, is_playing=playing, track_uri=track, duration_ms=dur, progress_ms=progress)


def item(uri, played_at, dur=200_000):
    return {"played_at": played_at.isoformat() + "Z", "track": {"uri": uri, "duration_ms": dur}}


class PollingTests(unittest.TestCase):
    def test_playing_stays_fast_and_end_is_tighter(self):
        self.assertEqual(poller.next_delay(snap(), 5), 4.0)
        self.assertEqual(poller.next_delay(snap(progress=195_000)), 1.5)

    def test_idle_backs_off_then_resets(self):
        idle = snap(track=None, playing=False)
        ds = [poller.next_delay(idle, n) for n in range(8)]
        self.assertEqual(ds[:5], [10.0, 10.0, 20.0, 30.0, 60.0])
        self.assertEqual(max(ds), 60.0)
        self.assertEqual(poller.next_delay(idle, poller.LONG_IDLE_POLLS), 120.0)
        self.assertEqual(poller.next_delay(snap(), 0), 4.0)           # playing again: fast immediately
        self.assertEqual(poller.next_delay(snap(playing=False), 3), 30.0)   # paused backs off too

    def test_gap_detection(self):
        self.assertFalse(poller.is_gap(5, 4))
        self.assertFalse(poller.is_gap(100, 60))                      # long planned delay is not a gap
        self.assertTrue(poller.is_gap(900, 4))                        # laptop slept

    def test_reconciler_skips_plays_the_poller_already_has(self):
        existing = [("a", T0, 200_000)]
        # recently-played stamps the play near its end
        self.assertEqual(missing_recent([item("a", T0 + timedelta(seconds=198))], existing), [])
        self.assertEqual(missing_recent([item("a", T0 + timedelta(seconds=198), dur=0)], existing)[0]["track"]["uri"], "a")
        # a repeat of the same track later in the evening is a different play
        got = missing_recent([item("a", T0 + timedelta(hours=3))], existing)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["_played_at"], T0 + timedelta(hours=3))

    def test_reconciler_fills_a_missed_track(self):
        got = missing_recent([item("b", T0), item("a", T0 + timedelta(seconds=60))], [("a", T0 - timedelta(seconds=120), 0)])
        self.assertEqual([g["track"]["uri"] for g in got], ["b"])


if __name__ == "__main__":
    unittest.main()
