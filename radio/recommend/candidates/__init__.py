"""Candidate generation from open data (no Spotify features). Each generator returns Candidate lists."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    artist_mbid: str
    artist_name: str
    score: float            # generator-native similarity, higher = closer
    source: str             # e.g. 'listenbrainz'
    seed_mbid: str          # the artist of yours that surfaced it
