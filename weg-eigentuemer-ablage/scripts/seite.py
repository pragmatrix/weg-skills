#!/usr/bin/env python3
"""Findet die PDF-Seite zu einem Suchmuster, für die Seitenangabe eines Quellenlinks.

Aufruf:
    python3 seite.py MUSTER DATEI...    (`just seite MUSTER DATEI...`)

MUSTER ist ein regulärer Ausdruck nach Python, Groß- und Kleinschreibung zählen nicht. DATEI ist ein PDF oder seine
Text-MD (`X.pdf` → `X.md`, erzeugt von `pdf2md.py`). Ausgegeben wird je Treffer `Datei S. N: Zeile`. Die Seite
ist die Seite der PDF-Datei. Sie steht in der Text-MD als Überschrift `## Seite N`.
"""
import re
import sys
from pathlib import Path

PAGE = re.compile(r"## Seite (\d+)$")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pattern = re.compile(sys.argv[1], re.I)
    hits = 0
    for name in sys.argv[2:]:
        md = Path(name).with_suffix(".md")
        if not md.exists():
            print(f"{name}: keine Text-MD", file=sys.stderr)
            continue
        page = None
        for line in md.read_text(encoding="utf-8").split("\n"):
            m = PAGE.match(line)
            if m:
                page = m.group(1)
            elif page and pattern.search(line):
                hits += 1
                print(f"{name} S. {page}: {line.strip()[:160]}")
    if not hits:
        sys.exit(1)


if __name__ == "__main__":
    main()
