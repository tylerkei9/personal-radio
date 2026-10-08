# Privacy, your data, and Spotify's rules

Read this before you install it. It is short.

## What is stored, and where

Everything is stored **on your own computer**, in the `data` folder. Nothing is uploaded anywhere by this program.
(It does look things up on the public music databases, MusicBrainz and ListenBrainz, which means those services
see song and artist codes from your library, not your name or account. One exception: if you set the optional
`RADIO_CONTACT` setting to an email or web address, which MusicBrainz asks for, it is sent along with those requests.)

| File in `data/` | What is in it |
|---|---|
| `radio.duckdb` | Each play (song, artist, time, how long you listened, how it started), your saved songs, followed artists, Spotify's "top" lists, and raw snapshots of what was playing |
| `radio_ids.duckdb` | Which Spotify song matches which public-database ID, and your taste basis |
| `radio_recs.duckdb` | Every song the tool has recommended, why, and how likely it was to be chosen |
| `.spotify_cache` | Your Spotify login token. **Treat it like a password.** |
| `.api_cache/` | Saved answers from the public databases and Spotify lookups |
| `radio.log`, `heartbeat.json`, `playlist_state.json` | Housekeeping |

The `data` folder is excluded from Git, so putting the project on GitHub does **not** publish any of it.
Never copy `data` into a public place. Never share `.spotify_cache` or your Client secret.

## What the program does automatically to limit data

- Raw "what was playing" snapshots are deleted after **30 days**.
- Saved Spotify search results are deleted after **24 hours**.
- Your plays, saves and recommendations are kept, because the recommender learns from them.

## Erasing things

```
python -m radio privacy                       # shows what is stored and how much is old
python -m radio privacy --purge               # deletes the old data now
python -m radio privacy --disconnect --yes    # deletes ALL Spotify-derived data, saved lookups and your login token
```

Stop the watcher before using the last two. After `--disconnect`, also remove the app's access at
**spotify.com/account/apps** so the token is dead on Spotify's side too.

## Spotify's developer rules: a real, unresolved risk

Using Spotify's API means accepting its Developer Policy. As summarised in this project's research (and not yet
read in full by the project owner), the policy includes rules such as:

- "Do not analyze the Spotify Content or the Spotify Service for any purpose" (III.13)
- "Do not use the Spotify Platform or any Spotify Content to train a machine learning or AI model" (III.14)
- Do not build something that replaces a core Spotify experience (III.11)

Turning your skips and finishes into likes and dislikes is arguably "analysis". Nobody here can tell you for
certain how Spotify would see it. The realistic worst case is that Spotify disables the developer app's key, not a
legal action, but this is not legal advice. The design reduces the exposure:

- It only stores minimal details about songs (an ID, name, artist, times), not Spotify's audio data.
- It learns from open databases, not from Spotify content.
- It expires raw Spotify data on a timer and has a one-command erase.
- Your own downloaded Extended Streaming History (which Spotify gives you as your personal data) is the cleanest
  thing to learn from, which is one reason to request it.

**Please read the policy yourself** at developer.spotify.com/policy before relying on this tool, and decide
whether you are comfortable with it.

## If you publish or share the project

The code contains no passwords, keys, or listening data. Before sharing your own copy, check that `data/` and any
`.env` file are not included (the supplied `.gitignore` already excludes them).
