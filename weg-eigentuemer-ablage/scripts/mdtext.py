#!/usr/bin/env python3
"""Lesetext einer eigenen Markdown-Datei: Links ohne Linkziel und Tooltip.

Aufruf:
    python3 mdtext.py DATEI    gibt den Lesetext aus (`just plain DATEI`)

Aus `[Text](<Pfad> "Tooltip")` und `[Text](Pfad)` wird `[Text]`. So lässt sich eine lange Ausarbeitung mit vielen
Quellenlinks lesen, und `wortdiff.py` vergleicht zwei Fassungen nur im sichtbaren Text.
"""
import re
import sys

LINK_TARGET = re.compile(r'\]\((?:<[^>]*>|[^)\s]+)(?:\s+"[^"]*")?\)')


def plain(text):
    """Text ohne Linkziele und Tooltips. Der Linktext bleibt in eckigen Klammern stehen."""
    return LINK_TARGET.sub("]", text)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        sys.stdout.write(plain(f.read()))
