import unittest

import duckdb

from radio import db
from radio.taste.basis import playlist_tracks, sync_basis


class FakeSp:
    def __init__(self, pages): self.pages = pages
    def _get(self, path, limit=50, offset=0):
        items = self.pages[offset // 50]
        return {"items": items, "next": "x" if offset // 50 + 1 < len(self.pages) else None}


def it(uri, key="item", **kw):
    return {key: {"uri": uri}, "added_at": "2026-01-02T03:04:05Z", **kw}


class BasisTests(unittest.TestCase):
    def test_playlist_tracks_handles_keys_pages_and_skips(self):
        sp = FakeSp([[it("spotify:track:a"), it("spotify:episode:e"), it("spotify:track:l", is_local=True)],
                     [it("spotify:track:b", key="track")]])
        self.assertEqual([u for u, _ in playlist_tracks(sp, "pl")], ["spotify:track:a", "spotify:track:b"])

    def test_sync_merges_liked_and_playlist(self):
        ev, ids = duckdb.connect(":memory:"), duckdb.connect(":memory:")
        ev.execute(db.SCHEMA); ids.execute(db.IDS_SCHEMA)
        ev.execute("INSERT INTO saves VALUES (now(), 'spotify:track:a')")
        counts = sync_basis(FakeSp([[it("spotify:track:a"), it("spotify:track:b")]]), ids, ev, {"Chill": "pl"})
        self.assertEqual(counts, {"liked": 1, "playlist:Chill": 2})
        self.assertEqual(ids.execute("SELECT count(DISTINCT track_uri) FROM basis_tracks").fetchone()[0], 2)
        sync_basis(FakeSp([[]]), ids, ev, {"Chill": "pl"})            # rebuild, not append
        self.assertEqual(ids.execute("SELECT count(*) FROM basis_tracks").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
