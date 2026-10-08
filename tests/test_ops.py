import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

import duckdb

from radio import db
from radio.collect.health import check, write_heartbeat
from radio.taste.ids import resolve_mbids
from radio.timeutil import hour_weekday


class OpsTests(unittest.TestCase):
    def test_local_time_handles_dst(self):
        ny = ZoneInfo("America/New_York")
        self.assertEqual(hour_weekday(datetime(2026, 10, 8, 1, 30), ny), (21, 2))     # EDT = UTC-4, Wed
        self.assertEqual(hour_weekday(datetime(2026, 12, 8, 1, 30), ny), (20, 0))     # EST = UTC-5, Mon

    def test_heartbeat_fresh_and_stale(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "hb.json")
            self.assertFalse(check(p)[0])                       # missing file
            write_heartbeat(p, status="playing")
            self.assertTrue(check(p, 60)[0])
            ok, msg = check(p, 60, now=lambda: __import__("time").time() + 600)
            self.assertFalse(ok)
            self.assertIn("STALE", msg)

    def test_mb_backoff_gives_up_after_streak(self):
        con = duckdb.connect(":memory:")
        con.execute(db.IDS_SCHEMA)
        con.executemany("INSERT INTO track_ids (track_uri, isrc) VALUES (?, ?)", [(f"u{i}", f"I{i}") for i in range(10)])
        calls, sleeps = [], []
        def boom(i):
            calls.append(i); raise OSError("503")
        self.assertEqual(resolve_mbids(con, fetch=boom, sleep=sleeps.append, max_fail_streak=3), 0)
        self.assertEqual(len(calls), 3)                          # stopped, did not hammer all 10
        self.assertTrue(sleeps[1] > sleeps[0])                   # exponential
        self.assertEqual(con.execute("SELECT count(mb_checked_at) FROM track_ids").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
