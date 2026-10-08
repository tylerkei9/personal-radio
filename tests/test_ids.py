import unittest

import duckdb

from radio import db
from radio.taste.ids import norm_isrc, parse_mb_recordings, resolve_mbids, seed_tracks, uri_to_id


class IdsTests(unittest.TestCase):
    def test_uri_to_id(self):
        self.assertEqual(uri_to_id("spotify:track:abc"), "abc")
        self.assertIsNone(uri_to_id("spotify:episode:abc"))

    def test_norm_isrc(self):
        self.assertEqual(norm_isrc('qz-l38-24-68720'), 'QZL3824 68720'.replace(' ', ''))
        self.assertIsNone(norm_isrc(None))

    def test_parse_mb(self):
        d = {"recordings": [{"id": "r1", "artist-credit": [{"artist": {"id": "a1"}}]}]}
        self.assertEqual(parse_mb_recordings(d), ("r1", "a1"))
        self.assertEqual(parse_mb_recordings({"recordings": []}), (None, None))

    def test_seed_and_resolve_with_fake_fetch(self):
        ev = duckdb.connect(":memory:")
        ev.execute(db.SCHEMA)
        ev.execute("INSERT INTO plays (source, started_at, track_uri, isrc) VALUES "
                   "('poller', now(), 'spotify:track:a', 'ISRC-1'), ('history', now(), 'spotify:track:b', NULL)")
        ev.execute("INSERT INTO saves VALUES (now(), 'spotify:track:c')")
        con = duckdb.connect(":memory:")
        con.execute(db.IDS_SCHEMA)
        self.assertEqual(seed_tracks(con, ev), 3)
        hits = resolve_mbids(con, fetch=lambda i: {"recordings": [{"id": "rec-" + i}]}, sleep=lambda s: None)
        self.assertEqual(hits, 1)
        self.assertEqual(con.execute("SELECT recording_mbid FROM track_ids WHERE track_uri='spotify:track:a'").fetchone()[0],
                         "rec-ISRC1")
        # misses are marked checked, not retried; the ISRC-less track stays untouched
        self.assertEqual(resolve_mbids(con, fetch=lambda i: 1 / 0, sleep=lambda s: None), 0)


if __name__ == "__main__":
    unittest.main()
