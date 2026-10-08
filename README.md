# Personal Radio

A private tool that learns your music taste from what you actually listen to on Spotify, then builds you a
weekly playlist of songs you have not heard yet.

It is made for one person (you). It runs on your own computer. Nothing is shared with anyone.

## What it does

1. **Watches your listening.** A small background program checks your Spotify account every few seconds and notes
   what you played, what you skipped, and what you let finish. It works for any device on your account, including
   your phone.
2. **Learns from it.** A song you finish counts as a "like". A song you skip in the first few seconds counts as a
   "no". Songs you saved to Liked Songs count as strong likes.
3. **Finds new music.** It looks up which songs people with similar taste play together (using free, public music
   databases, not Spotify's recommendations) and filters out remixes, live versions and very mainstream picks.
4. **Builds a playlist.** Once a week it creates a private Spotify playlist called
   **"Personal Radio - Weekly Auto"** with 30 songs. About half are close matches, some are songs by artists you
   already like that you have not heard, and the rest are experiments so the tool can keep learning.

## What you need

- A Windows or Mac computer that stays on (the watcher only sees what plays while it runs)
- Spotify **Premium** (Spotify requires it for the developer app this tool uses)
- Python 3.11 or newer (free, from python.org)
- About 30 minutes for the first setup

## Start here

| I want to... | Read |
|---|---|
| Set it up on my PC, step by step | [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) |
| Understand how it decides things | [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) |
| Know what is stored and how to erase it | [docs/PRIVACY.md](docs/PRIVACY.md) |
| Move everything from another computer, or read the full project history and research | [docs/MIGRATION_PACKAGE.md](docs/MIGRATION_PACKAGE.md) |

## The commands you will use

Type these in a terminal from the project folder. Replace `python` with `.venv\Scripts\python` on Windows or
`.venv/bin/python` on Mac if you set it up the way the guide shows.

| Command | What it does |
|---|---|
| `python -m radio track` | Starts watching your listening. Leave it running. |
| `python -m radio health` | Tells you whether the watcher is still alive. |
| `python -m radio identify` | Matches your songs to the public music databases. Run it before your first playlist. |
| `python -m radio playlist` | **Preview** this week's playlist. Nothing is changed in Spotify. |
| `python -m radio playlist --write` | Create or refresh the playlist in your Spotify account. |
| `python -m radio import-history FILE` | Load your downloaded Spotify "Extended Streaming History". |
| `python -m radio privacy` | See what is stored. Add `--purge` to delete old data, or `--disconnect --yes` to erase everything. |
| `python -m radio` | Lists all commands. |

## What is in this folder

```
radio/        the program (see below)
config/       your settings (which playlists count as "your taste")
data/         YOUR data: listening history, Spotify login, saved lookups. Created on first run. Never uploaded.
docs/         guides and the full project history
scripts/      a helper that makes the watcher start automatically on Windows
tests/        automatic checks that the program still works
```

Inside `radio/`:

| Folder | Job |
|---|---|
| `collect/` | Watches Spotify and saves what you played |
| `taste/` | Turns plays into likes and dislikes, and identifies songs |
| `recommend/` | Finds new songs and builds the playlist |
| `evalkit/` | Measures whether the recommendations beat simple guesses (needs a few weeks of data) |

## Honest status

| Part | State |
|---|---|
| Watching and saving your listening | Works. Runs best on a computer that is always on. |
| Weekly playlist | Works when you run it by hand. It does not yet run itself on a schedule. |
| Loading your Extended Streaming History | Written, but not yet tried on a real export (you must request it from Spotify first). |
| Measuring whether it is any good | Built, but needs several weeks of listening data before the numbers mean anything. |
| Fancier learning methods | Deliberately not built yet; the research says they need far more data than one person produces. |

Known quirk: the playlist this tool created has twice vanished from the Spotify account for reasons not yet
known. The tool notices and makes a new one, so if your playlist is replaced by a new copy, that is why.

## Running the checks

```
python -m unittest discover -s tests -t .
```

A line ending in `OK` means everything passes. (Some warning lines about "musicbrainz lookup failed" are expected;
they come from a test that pretends the service is down.)
