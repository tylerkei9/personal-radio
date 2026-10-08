"""Where everything lives. The only module that knows file locations.

Code is in `radio/`; everything personal (your listening data, the Spotify login token, caches, logs) is in `data/`,
which is never committed to git. Set RADIO_HOME to keep that folder somewhere else.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RADIO_HOME", os.path.join(ROOT, "data"))
CONFIG = os.path.join(ROOT, "config")

EVENTS_DB = os.path.join(DATA, "radio.duckdb")          # what you played (written by the tracker)
IDS_DB = os.path.join(DATA, "radio_ids.duckdb")         # song identity map + taste basis
RECS_DB = os.path.join(DATA, "radio_recs.duckdb")       # every recommendation made, with its probability
SPOTIFY_TOKEN = os.path.join(DATA, ".spotify_cache")    # your Spotify login (keep private)
API_CACHE = os.path.join(DATA, ".api_cache")            # saved answers from ListenBrainz / MusicBrainz / Spotify
HEARTBEAT = os.path.join(DATA, "heartbeat.json")        # "the tracker is alive" signal
PLAYLIST_STATE = os.path.join(DATA, "playlist_state.json")
LOG = os.path.join(DATA, "radio.log")
TASTE_BASIS = os.path.join(CONFIG, "taste_basis.json")  # which playlists count as "my taste"

os.makedirs(DATA, exist_ok=True)
