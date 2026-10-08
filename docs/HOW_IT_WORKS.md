# How it works

A plain-language tour. No maths. Technical detail and the research behind each choice are in
[MIGRATION_PACKAGE.md](MIGRATION_PACKAGE.md).

## The big picture

```
 your listening ──> [1. Watch] ──> [2. Learn what you like] ──> [3. Find candidates] ──> [4. Choose] ──> playlist
   (Spotify)        saved plays      likes and "no"s               songs similar          30 songs
                                                                   listeners play
```

## 1. Watch

Every few seconds the program asks Spotify, "what is this account playing right now?". From those snapshots it
works out each play: which song, when it started, how long you listened, and whether you skipped, finished, or
replayed it. It also notes how the play began: you picked it, or it continued by itself from a playlist or album.

To save effort it checks less often when nothing is playing (down to once a minute, then once every two minutes
late at night). Once an hour it also asks Spotify for your "recently played" list and fills in anything it missed,
such as while the computer was asleep. If it detects a long silence, it does this catch-up straight away.

Plays recorded through that catch-up list count as "you heard it" but cannot say whether you skipped, because
Spotify does not provide that detail there.

Private Session plays in Spotify cannot be seen at all.

## 2. Learn what you like

Each play becomes a score:

| What happened | Meaning |
|---|---|
| Finished the song | A mild like |
| Finished it **and** later saved it, or played it again within a day | A strong like |
| Skipped in the first 10 seconds | A strong no |
| Skipped between 10 and 30 seconds | A no |
| Skipped after 30 seconds | A mild no |
| Stopped the music partway | Ignored (no evidence either way) |

Two fairness rules matter:

- **A save only counts for plays that came before it** (within a week). Saving a song you have loved for years
  says nothing about one particular play today, so it is recorded as "already familiar" instead of as proof.
- **Autoplay counts as much as songs you chose by hand.** The tool is being judged on what it suggests, and
  suggestions usually arrive as autoplay.

Your Liked Songs, and any playlists you list in `config/taste_basis.json`, are your "taste basis": the songs the
recommender treats as the definition of you. Older likes count a little less (they fade by half over a year).

## 3. Find candidates

Spotify's own recommendation tools are closed to this kind of app, so the tool uses free public databases:

- **MusicBrainz** gives every song and artist a permanent ID, so songs can be matched across services.
- **ListenBrainz** publishes which songs people tend to play in the same listening session.

For each song in your taste basis, it asks ListenBrainz, "what do people who play this also play?". Then three
corrections stop the list from being just "the most famous songs":

1. **Two-way check.** A song only counts as similar if it points back at your song too. Very popular songs are
   "similar" to everything, and this removes them.
2. **Breadth discount.** A song that appears for dozens of unrelated seeds is likely just popular, not a good fit.
3. **Popularity discount.** Extremely well-known songs are marked down, so more hidden gems surface.

It then drops remixes, live versions, karaoke, "sped up" edits and compilation-only tracks, keeps at most one song
per album, and finds each song on Spotify using its exact recording code (ISRC).

Coverage is partial: roughly four in ten of your songs currently have neighbours in the public data. That limits
how many candidates exist, and it will improve as more of your songs are matched.

## 4. Choose the 30 songs

| Share | Kind | Where it comes from |
|---|---|---|
| 50% (15) | **Confident** | The best-scoring new songs by new artists |
| 20% (6) | **Deep cuts** | Songs you have not heard by artists you already like (less famous ones are favoured) |
| 20% (6) | **Explore** | Picked at random, with better-scoring songs more likely |
| 10% (3) | **Wildcard** | Picked completely at random from the rest |

Why include random picks? If the tool only ever played its best guesses, it could never discover that it was
wrong. The random picks are small, honest experiments. The tool records, for every song, **how likely it was to be
chosen**. That record is what later allows a fair measurement of whether the tool is any good, rather than a
self-flattering one. The order of the 30 songs is shuffled so a song's position does not reveal how it was
chosen, and the tool never recommends the same song twice.

## 5. Measure

`python -m radio evaluate` compares the recommender against dumb baselines (such as "just replay what I played
recently"). A recommender that cannot beat those is not worth trusting. It needs a few weeks of data before the
numbers mean anything, and the honest answer for the first month may be "not enough data yet".

## What it deliberately does not do

- It does not use Spotify's audio-feature or recommendation endpoints (Spotify closed them to new apps).
- It does not train a neural network. With one listener's history, simple methods win, and Spotify's rules
  restrict training machine-learning models on Spotify content anyway. See [PRIVACY.md](PRIVACY.md).
- It does not change your Liked Songs or any playlist except its own.

## Glossary

| Word | Meaning |
|---|---|
| **API** | The official way for a program to talk to a service such as Spotify |
| **Developer app** | The small registration that gives this program permission to use Spotify's API |
| **Poller / watcher / tracker** | The background program that checks what is playing |
| **ISRC** | A code that identifies one specific recording of a song, like a barcode |
| **MBID** | A MusicBrainz ID: a permanent code for a song or artist in the public database |
| **ListenBrainz / MusicBrainz** | Free, non-profit music databases run by the MetaBrainz Foundation |
| **Label** | The program's judgement of one play: like, no, or unclear |
| **Seed** | A song or artist of yours that the search for new music starts from |
| **Propensity** | The recorded chance that a particular song would be chosen for the playlist |
| **Extended Streaming History** | The full record of your listening that Spotify will send you on request |
| **Cache** | A saved copy of an answer, so the program does not ask the same question twice |
| **Heartbeat** | A small file the watcher rewrites constantly so you can tell it is alive |
| **DuckDB** | The simple database format used for the files in `data/` |
