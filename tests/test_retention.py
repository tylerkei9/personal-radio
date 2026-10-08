import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta

import duckdb

from radio import db, retention
from radio.recommend.candidates import cache

NOW = datetime(2026, 10, 8, 12, 0, 0)


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cache.CACHE_DIR = os.path.join(self.tmp.name, "cache")
        self.ev, self.ids, self.recs = (duckdb.connect(":memory:") for _ in range(3))
        self.ev.execute(db.SCHEMA); self.ids.execute(db.IDS_SCHEMA); self.recs.execute(db.RECS_SCHEMA)

    def test_cache_routes_spotify_keys_to_subdir(self):
        cache.cached("sp-isrc:X", lambda: [{"track_uri": "u"}])
        cache.cached("lb-simrec:Y", lambda: [1])
        self.assertTrue(os.path.exists(cache.cache_path("sp-isrc:X")))
        self.assertEqual(os.path.basename(os.path.dirname(cache.cache_path("sp-isrc:X"))), "spotify")
        self.assertEqual(os.path.dirname(cache.cache_path("lb-simrec:Y")), cache.CACHE_DIR)

    def test_purge_old_raw_events_and_spotify_cache_only(self):
        self.ev.execute("INSERT INTO raw_events VALUES (?, 'poll', '{}'), (?, 'poll', '{}')",
                        [NOW - timedelta(days=31), NOW - timedelta(days=2)])
        self.ev.execute("INSERT INTO plays (source, started_at, track_uri) VALUES ('poller', ?, 'u')", [NOW - timedelta(days=400)])
        cache.cached("sp-isrc:old", lambda: [{"track_uri": "u"}])
        cache.cached("sp-isrc:new", lambda: [{"track_uri": "u"}])
        cache.cached("mb-rec:keep", lambda: {"title": "t"})
        old = cache.cache_path("sp-isrc:old")
        os.utime(old, (time.time() - 3 * 86400,) * 2)
        legacy = os.path.join(cache.CACHE_DIR, "legacy.json")                 # pre-subdir Spotify cache file
        json.dump([{"track_uri": "u", "track_name": "n"}], open(legacy, "w"))
        res = retention.purge(self.ev, now=NOW)
        self.assertEqual(res["raw_events_deleted"], 1)
        self.assertEqual(res["cache_files_deleted"], 2)                       # the stale subdir file + the legacy one
        self.assertEqual(self.ev.execute("SELECT count(*) FROM raw_events").fetchone()[0], 1)
        self.assertEqual(self.ev.execute("SELECT count(*) FROM plays").fetchone()[0], 1)   # plays are kept
        self.assertTrue(os.path.exists(cache.cache_path("sp-isrc:new")))
        self.assertTrue(os.path.exists(cache.cache_path("mb-rec:keep")))
        self.assertFalse(os.path.exists(old))

    def test_disconnect_deletes_everything_spotify_derived(self):
        self.ev.execute("INSERT INTO plays (source, started_at, track_uri) VALUES ('poller', ?, 'u')", [NOW])
        self.ev.execute("INSERT INTO saves VALUES (?, 'u')", [NOW])
        self.ids.execute("INSERT INTO track_ids (track_uri) VALUES ('u')")
        self.ids.execute("INSERT INTO basis_tracks VALUES ('liked', 'u', ?)", [NOW])
        self.recs.execute("INSERT INTO picks VALUES ('p', ?, 0, 'u', 'n', 'a', NULL, 'confident', 1, 1, 'r')", [NOW])
        cache.cached("sp-isrc:x", lambda: [{"track_uri": "u"}])
        tok = os.path.join(self.tmp.name, ".spotify_cache")
        open(tok, "w").write("{}")
        res = retention.disconnect(self.ev, self.ids, self.recs, token_path=tok)
        self.assertEqual((res["plays"], res["saves"], res["track_ids"], res["picks"], res["token_removed"]), (1, 1, 1, 1, True))
        for con, t in ((self.ev, "plays"), (self.ev, "saves"), (self.ids, "track_ids"), (self.ids, "basis_tracks"), (self.recs, "picks")):
            self.assertEqual(con.execute(f"SELECT count(*) FROM {t}").fetchone()[0], 0)
        self.assertFalse(os.path.exists(tok))
        self.assertFalse(os.path.exists(cache.CACHE_DIR))


if __name__ == "__main__":
    unittest.main()
