# Getting started (Windows PC)

This guide assumes no programming experience. Take it one step at a time. Mac users: the steps are the same;
use Terminal instead of PowerShell and `.venv/bin/python` instead of `.venv\Scripts\python`.

## Part 1: One-time preparation

### 1. Install Python
Download Python 3.11 or newer from **python.org/downloads**. In the installer, tick **"Add Python to PATH"**
before clicking Install.

### 2. Get the project onto the PC
Either download it from GitHub (green **Code** button, then **Download ZIP**, then unzip it) or, if you use Git,
clone it. Put the folder somewhere permanent, such as `C:\PersonalRadio`.

### 3. Open PowerShell in that folder
In File Explorer, open the project folder, click the address bar, type `powershell`, and press Enter.

### 4. Install the program's parts
Copy and paste these two lines, one at a time:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

The first creates a private workspace for the program. The second installs the two libraries it needs.

## Part 2: Connect to Spotify

You create a small "developer app" that gives the program permission to read your listening. It is free, but the
account that owns it must have Spotify Premium.

1. Go to **developer.spotify.com/dashboard** and log in.
2. Click **Create app**. Name it anything (for example "Personal Radio").
3. In **Redirect URI**, enter exactly: `http://127.0.0.1:8888/callback` and click Add.
4. Tick **Web API**, agree to the terms, and Save.
5. Open the app's **Settings**. You will see a **Client ID** and a **Client secret** (click "View client secret").
   Keep the secret private. It is like a password for the app. Never paste it into a public place.

### Start the watcher for the first time
In PowerShell, in the project folder:

```
.venv\Scripts\python -m radio track
```

It asks for three things:
- **SPOTIPY_CLIENT_ID**: paste your Client ID
- **SPOTIPY_CLIENT_SECRET**: paste your Client secret (nothing appears on screen as you type; that is normal)
- **SPOTIPY_REDIRECT_URI**: just press Enter to accept the default

A browser window opens asking you to approve access. Click **Agree**. The browser may then show an error page;
that is fine. Copy the full address from the browser's address bar and paste it back into PowerShell if it asks.

Play a song in Spotify. After a minute, open a second PowerShell window and run
`.venv\Scripts\python -m radio health`. It should say `ok`.

To stop it, press `Ctrl+C` in its window.

### Make it start by itself
So you never have to remember: stop the watcher (Ctrl+C), then run

```
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows_task.ps1
```

This adds a Windows task that starts the watcher when you log in and restarts it if it crashes. To remove it later:
`Unregister-ScheduledTask PersonalRadio`.

Your PC must be awake for the watcher to work. In Windows settings, set "Sleep" to Never while plugged in.

## Part 3: Get your first playlist

Wait until the watcher has run for a few days, or load your history first (Part 4). Then:

```
.venv\Scripts\python -m radio identify
.venv\Scripts\python -m radio playlist
```

The second command only **previews** a list of 30 songs and what each one is based on. Nothing changes in
Spotify. If it looks good:

```
.venv\Scripts\python -m radio playlist --write
```

Open Spotify and look for the private playlist **"Personal Radio - Weekly Auto"**. Run the same command each week
for a fresh list. Songs it has recommended before are never repeated.

Optional: to count another playlist as part of your taste (for example a "Chill" playlist), copy
`config\taste_basis.example.json` to `config\taste_basis.json` and replace the example with your playlist's name
and ID. (A playlist's ID is the long code in its share link after `playlist/`.) Nothing is added to your Liked Songs.

## Part 4: Load your full listening history (strongly recommended)

Spotify will give you your complete listening history for free. It makes the tool much smarter on day one.

1. Go to **spotify.com/account/privacy** and scroll to **Download your data**.
2. Tick **Extended streaming history** and click **Request data**.
3. Click the confirmation link Spotify emails you.
4. Wait (it can take up to 30 days). When the email arrives, download the ZIP.
5. Run:
   ```
   .venv\Scripts\python -m radio import-history C:\path\to\the-file.zip
   ```

This feature is written but has not yet been tried on a real export. If it complains, send the error message to
whoever is maintaining the project; it is likely a small fix.

## Part 5: Moving from another computer (for example from the Mac)

1. **Stop the watcher on the old computer** (Ctrl+C). Two watchers on one account would record everything twice.
2. Copy the old project's **`data`** folder and **`config`** folder into the new project folder, replacing what is
   there. The `data` folder holds your history, your Spotify login and saved lookups.
3. Continue from Part 2, "Start the watcher". You will be asked for the Client ID and Client secret again (they
   are deliberately not stored in the project). Because your Spotify login came with the `data` folder, the browser
   approval may not be needed; if it asks, approve it again.

The file [MIGRATION_PACKAGE.md](MIGRATION_PACKAGE.md) has the full background if anything is unclear.

## If something goes wrong

| What you see | What to do |
|---|---|
| `python` is not recognized | Reinstall Python and tick "Add Python to PATH". Restart PowerShell. |
| `health` says STALE | The watcher is not running or the PC slept. Start it again. |
| Browser shows an error after approving Spotify | Normal. Copy the address from the address bar and paste it into PowerShell if asked. |
| `playlist` says there is nothing to recommend | Run `identify` first, and make sure you have a few days of plays or have imported your history. |
| Spotify says "Too many requests" (HTTP 429) | The program waits and retries by itself. Do nothing. |
| "write not confirmed" or the playlist vanished | Run `playlist --write` again. It creates a new one. |
| Anything else | Look at the end of `data\radio.log`; it records what the watcher was doing. |
