import unittest
from datetime import datetime, timedelta

from radio.taste.labels import label_play, skip_streaks
from radio.collect.tracker import Snapshot, Tracker
from radio.collect.history_import import parse_row

T0 = datetime(2026, 10, 7, 12, 0, 0)


def snap(t, prog, uri="spotify:track:a", dur=200_000, playing=True):
    return Snapshot(ts=T0 + timedelta(seconds=t), is_playing=playing, track_uri=uri,
                    name="n", artist="x", duration_ms=dur, progress_ms=prog)


class TrackerTests(unittest.TestCase):
    def test_completed(self):
        tr = Tracker()
        for t in range(0, 200, 4):
            tr.update(snap(t, t * 1000))
        tr.update(snap(199, 198_000))
        tr.update(snap(201, 1_000, uri="spotify:track:b"))
        (p,) = tr.drain()
        self.assertEqual(p["end_reason"], "completed")

    def test_completed_when_last_poll_lands_5s_short(self):
        tr = Tracker()
        for t in range(0, 196, 4):
            tr.update(snap(t, t * 1000))
        tr.update(snap(195, 194_600))             # last sample 5.4s before the end (old 4s window => "skipped")
        tr.update(snap(201, 1_000, uri="spotify:track:b"))
        (p,) = tr.drain()
        self.assertEqual(p["end_reason"], "completed")

    def test_skip(self):
        tr = Tracker()
        tr.update(snap(0, 0)); tr.update(snap(4, 4000))
        tr.update(snap(6, 500, uri="spotify:track:b"))
        (p,) = tr.drain()
        self.assertEqual((p["end_reason"], p["ms_played"]), ("skipped", 4000))

    def test_repeat_splits_plays(self):
        tr = Tracker()
        tr.update(snap(0, 0)); tr.update(snap(198, 198_000)); tr.update(snap(200, 1_000))
        (p,) = tr.drain()
        self.assertEqual(p["end_reason"], "completed")
        self.assertIsNotNone(tr.cur)

    def test_pause_does_not_split(self):
        tr = Tracker()
        tr.update(snap(0, 0)); tr.update(snap(10, 10_000, playing=False)); tr.update(snap(300, 10_000))
        self.assertEqual(tr.drain(), [])


class ContextTests(unittest.TestCase):
    def test_start_kinds_and_seeks(self):
        from radio.collect.tracker import context_type
        self.assertEqual(context_type("spotify:artist:1"), "artist")
        self.assertEqual(context_type("spotify:user:me:collection"), "collection")
        self.assertEqual(context_type("spotify:user:me:playlist:9"), "playlist")
        self.assertIsNone(context_type(None))
        tr = Tracker()
        a = snap(0, 0); a.context_uri = "spotify:playlist:p"
        tr.update(a)
        tr.update(snap(100, 100_000));
        # seek forward 60s in one 4s poll
        s2 = snap(104, 164_000); s2.context_uri = "spotify:playlist:p"; tr.update(s2)
        b = snap(205, 500, uri="spotify:track:b"); b.context_uri = "spotify:playlist:p"
        tr.update(b)
        (p,) = tr.drain()
        self.assertEqual(p["seeks"], 1)         # only the 60s jump; 100s played in 100s is not a seek
        self.assertEqual(p["start_kind"], "user")
        c = snap(400, 0, uri="spotify:track:c"); c.context_uri = "spotify:artist:z"
        tr.update(c)
        self.assertEqual(tr.cur.start_kind, "user")   # new context after a gap => hand-picked

    def test_auto_chain(self):
        tr = Tracker()
        a = snap(0, 0, dur=10_000); a.context_uri = "spotify:album:x"
        tr.update(a)
        a2 = snap(8, 8_000, dur=10_000); a2.context_uri = "spotify:album:x"; tr.update(a2)
        b = snap(10, 500, uri="spotify:track:b"); b.context_uri = "spotify:album:x"
        tr.update(b)
        self.assertEqual(tr.cur.start_kind, "auto")

    def test_stop_at_end_is_completed(self):
        tr = Tracker()
        tr.update(snap(0, 0, dur=10_000)); tr.update(snap(9, 9_000, dur=10_000))
        tr.update(Snapshot(ts=T0 + timedelta(seconds=12), is_playing=False))
        self.assertEqual(tr.drain()[0]["end_reason"], "completed")


class LabelTests(unittest.TestCase):
    def test_grades(self):
        self.assertEqual(label_play(3000, 200_000, "skipped").name, "strong_neg")
        self.assertEqual(label_play(60_000, 200_000, "skipped").name, "weak_neg")
        self.assertEqual(label_play(200_000, 200_000, "completed").name, "weak_pos")
        self.assertEqual(label_play(200_000, 200_000, "completed", saved=True).name, "strong_pos")
        self.assertIsNone(label_play(1000, 200_000, "other"))
        self.assertIsNone(label_play(1000, 200_000, "skipped", incognito=True))

    def test_streaks(self):
        self.assertEqual(skip_streaks(["skipped", "skipped", "completed", "skipped"]), [1, 2, 0, 1])


class HistoryTests(unittest.TestCase):
    def test_parse(self):
        r = {"ts": "2025-01-02T03:04:05Z", "ms_played": 1234, "spotify_track_uri": "spotify:track:z",
             "master_metadata_track_name": "N", "master_metadata_album_artist_name": "A",
             "reason_end": "fwdbtn", "platform": "iOS", "shuffle": True, "incognito_mode": False}
        row = parse_row(r)
        self.assertEqual(row[8], "skipped")
        self.assertIsNone(parse_row({"ts": "2025-01-02T03:04:05Z", "spotify_track_uri": None}))


if __name__ == "__main__":
    unittest.main()
