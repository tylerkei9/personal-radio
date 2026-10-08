"""File-backed JSON cache for API responses (keeps API usage low; no DB lock contention)."""
import hashlib
import json
import os
import time

from radio import paths

CACHE_DIR = os.environ.get("RADIO_CACHE", paths.API_CACHE)


SPOTIFY_SUBDIR = "spotify"


def cache_path(key: str) -> str:
    """Spotify-derived entries (keys starting `sp-`) live in their own subdirectory so retention can purge them alone."""
    sub = SPOTIFY_SUBDIR if key.startswith("sp-") else ""
    return os.path.join(CACHE_DIR, sub, hashlib.sha1(key.encode()).hexdigest() + ".json")


def cached(key: str, fetch, ttl_s: float = 7 * 86400, now=time.time):
    """Return fetch() result, reusing a stored copy younger than ttl_s. Failures are not cached."""
    path = cache_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        if now() - os.path.getmtime(path) < ttl_s:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    data = fetch()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data
