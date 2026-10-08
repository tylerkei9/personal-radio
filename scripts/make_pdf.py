"""Build docs/MIGRATION_PACKAGE.pdf from docs/MIGRATION_PACKAGE.md.   python scripts/make_pdf.py

Needs pandoc and Google Chrome (both free). Pandoc turns the Markdown into one self-contained HTML page with the
figures embedded; headless Chrome prints it to PDF.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CSS = """
@page { size: A4; margin: 18mm 15mm 18mm 15mm; }
body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #1a1a19; max-width: none; }
h1 { font-size: 20pt; border-bottom: 2px solid #d9d8d2; padding-bottom: 4pt; break-before: page; }
h1:first-of-type { break-before: avoid; }
h2 { font-size: 14pt; margin-top: 18pt; } h3 { font-size: 11.5pt; } h4 { font-size: 10.5pt; }
h1, h2, h3, h4 { break-after: avoid; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 8pt 0; break-inside: auto; }
th, td { border: 1px solid #d9d8d2; padding: 3pt 5pt; vertical-align: top; overflow-wrap: anywhere; }
th { background: #efeee9; text-align: left; }
tr { break-inside: avoid; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.5pt; background: #efeee9; padding: 0 2pt; border-radius: 2pt; overflow-wrap: anywhere; }
pre { background: #efeee9; padding: 6pt; font-size: 8pt; white-space: pre-wrap; overflow-wrap: anywhere; break-inside: avoid; }
pre code { background: none; }
img { max-width: 100%; height: auto; break-inside: avoid; display: block; margin: 8pt 0; }
a { color: #1d5fb0; text-decoration: none; overflow-wrap: anywhere; }
blockquote { border-left: 3px solid #d9d8d2; margin-left: 0; padding-left: 10pt; color: #52514e; }
"""


def main():
    src = os.path.join(DOCS, "MIGRATION_PACKAGE.md")
    out = os.path.join(DOCS, "MIGRATION_PACKAGE.pdf")
    with tempfile.TemporaryDirectory() as tmp:
        css = os.path.join(tmp, "print.css"); html = os.path.join(tmp, "doc.html")
        open(css, "w").write(CSS)
        subprocess.run(["pandoc", src, "-f", "gfm", "-t", "html5", "-s", "--embed-resources", "--resource-path", DOCS,
                        "--metadata", "pagetitle=Personal Radio: Migration Package",
                        "-c", css, "-o", html], check=True)
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}",
                        "file://" + html], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("wrote", out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
