# Notes for Claude

Personal Radio: a private Spotify listening tracker and weekly playlist builder for one user. Python 3.11+,
dependencies `duckdb` and `spotipy`.

## Do not read these in full (they are very large)

- `docs/MIGRATION_PACKAGE.md` (about 310 KB). Background and research only. Use grep or read a single section if a
  question needs it. Sections 1 to 9 are the plain-language summary. Parts A to I are the technical record.
- `docs/images/*.svg` (generated; edit `scripts/figs_*.py` instead).

Everything needed to work on the code is in this file, `README.md`, and the code itself.

## Layout

- `radio/collect/` watches Spotify and stores plays (tracker, poller, sync, history import, health, run).
- `radio/taste/` labels plays and maps songs to MusicBrainz IDs (labels, pipeline, basis, ids).
- `radio/recommend/` builds candidates and the playlist (playlist, `candidates/`).
- `radio/evalkit/` baselines and metrics. `radio/retention.py` purge and disconnect. `radio/paths.py` all file locations.
- Entry point: `python -m radio <command>`. Run it with no command to list them.
- `data/` holds the user's private data and login token. It is git-ignored. Never commit it, print it, or read it into context.

## Commands

- Tests: `python -m unittest discover -s tests -t .` (58 tests, standard library only)
- Figures: `python scripts/make_diagrams.py`. PDF: `python scripts/make_pdf.py` (needs pandoc and Chrome).

## Rules

- Never ask for or store the Spotify client secret in files. It is entered at run time.
- Keep Spotify-derived data minimal and short-lived. Do not add features that train models on Spotify content.
- Figures must be ASCII only: no emoji, no special glyphs, no em dashes.
- Style for replies and docs: short, neutral, no em dashes.
- The playlist `--write` and any push to GitHub are outward-facing. Confirm before doing either.

## Current status and next steps

See the "Where things stand" and "What comes next" sections of `docs/MIGRATION_PACKAGE.md` (read just those).
In brief: import the Extended Streaming History when it arrives (`python -m radio import-history`, untested on a real
export), run the tracker on the always-on PC, then schedule the weekly playlist.
