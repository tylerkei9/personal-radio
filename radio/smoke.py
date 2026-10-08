"""Live API smoke test for playlist writes (Feb 2026 renames). Creates ONE private playlist, then tries to remove it.

Usage: python -m radio login-check      (one extra browser approval: adds the playlist-modify-private scope)
"""
from radio.collect.poller import build_client

URIS = ["spotify:track:4ZgXDDRSS4lVx1g3WkRon0", "spotify:track:1CKa6WJ6QvzWnTxC9j307B", "spotify:track:0j333QK40JyBgIYA3sn667"]


def step(name, fn):
    try:
        out = fn()
        print(f"OK    {name}")
        return out
    except Exception as e:
        print(f"FAIL  {name}: {str(e)[:200]}")


def main():
    sp = build_client(timeout=30)
    me = step("GET /me", sp.me)
    pl = step("POST /me/playlists", lambda: sp._post("me/playlists", payload={
        "name": "Personal Radio smoke test", "public": False, "description": "API test; safe to delete"}))
    if not pl and me:
        pl = step("POST /users/{id}/playlists (old path)", lambda: sp._post(
            f"users/{me['id']}/playlists", payload={"name": "Personal Radio smoke test", "public": False}))
    if not pl:
        return
    pid = pl["id"]
    step("POST /playlists/{id}/items (add 2)", lambda: sp._post(f"playlists/{pid}/items", payload={"uris": URIS[:2]}))
    step("PUT  /playlists/{id}/items (replace with 1)", lambda: sp._put(f"playlists/{pid}/items", payload={"uris": URIS[2:]}))
    items = step("GET  /playlists/{id}/items", lambda: sp._get(f"playlists/{pid}/items"))
    if items:
        print("      items now:", [(i.get("item") or i.get("track") or {}).get("name") for i in items["items"]])
    step("DELETE /playlists/{id}/followers (cleanup)", lambda: sp._delete(f"playlists/{pid}/followers"))


if __name__ == "__main__":
    main()
