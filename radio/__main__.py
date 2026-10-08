"""One front door for everything:  python -m radio <command> [options]

Run `python -m radio` with no command to see the list.
"""
import runpy
import sys

COMMANDS = {
    "track":          ("radio.collect.run",            "Watch your Spotify listening and save it (leave this running)"),
    "health":         ("radio.collect.health",         "Check that the tracker is alive (exit code 1 if it has gone quiet)"),
    "import-history": ("radio.collect.history_import", "Load your Extended Streaming History export (a .zip or folder)"),
    "playlist":       ("radio.recommend.playlist",     "Build this week's playlist (preview only; add --write to publish it)"),
    "identify":       ("radio.taste.ids",              "Match your songs to open music databases (needed for recommendations)"),
    "evaluate":       ("radio.evalkit.run",            "Score the recommender against simple baselines on your history"),
    "privacy":        ("radio.retention",              "Delete old data, or disconnect from Spotify and erase everything"),
    "login-check":    ("radio.smoke",                  "Test the Spotify connection"),
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help") or argv[0] not in COMMANDS:
        if argv and argv[0] not in ("-h", "--help", "help"):
            print(f"Unknown command: {argv[0]}\n")
        print("Usage: python -m radio <command> [options]\n\nCommands:")
        for name, (_, blurb) in COMMANDS.items():
            print(f"  {name:15s} {blurb}")
        return 0 if not argv or argv[0] in ("-h", "--help", "help") else 2
    module, _ = COMMANDS[argv[0]]
    sys.argv = [module] + argv[1:]
    runpy.run_module(module, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
