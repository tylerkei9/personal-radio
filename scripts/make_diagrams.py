"""Regenerate every figure in docs/images/.   python scripts/make_diagrams.py [--png DIR]

--png renders each SVG to a PNG with headless Chrome (for checking the layout by eye).
"""
import importlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(os.path.dirname(HERE), "docs", "images")
MODULES = ["figs_basics", "figs_logic", "figs_eval"]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    png = argv[argv.index("--png") + 1] if "--png" in argv else None
    only = [a for a in argv if a.startswith("only=")]
    for name in MODULES:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        for key, fn in mod.FIGS.items():
            if only and key.split("-")[0] not in only[0][5:].split(","):
                continue
            fig = fn()
            path = os.path.join(OUT, key + ".svg")
            with open(path, "w", encoding="ascii") as fh:
                fh.write(fig.svg())
            if png:
                os.makedirs(png, exist_ok=True)
                subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                                f"--screenshot={png}/{key}.png", f"--window-size={fig.w},{fig.h}", "file://" + path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("wrote", path)


if __name__ == "__main__":
    main(sys.argv[1:])
