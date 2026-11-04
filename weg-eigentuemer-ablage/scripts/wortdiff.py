#!/usr/bin/env python3
"""Zeigt, welche Wörter einer eigenen Markdown-Datei gegenüber dem Stand in Git weggefallen sind.

Aufruf:
    python3 wortdiff.py DATEI [REVISION]    Standard für REVISION ist HEAD (`just wortdiff DATEI`)

Verglichen wird nur der Lesetext aus `mdtext.py`, also ohne Linkziele und Tooltips. Wörter und Satzzeichen
zählen einzeln. Dadurch fällt nicht auf, wenn ein Quellenlink vor ein Satzzeichen gesetzt wird. Neue Wörter, etwa der
Linktext eines Quellenlinks, werden nicht gemeldet. Gemeldet wird jede Stelle, an der alter Text fehlt, mit
Zeilennummer im alten Stand. Das prüft nach dem Nachtragen von Quellenlinks, dass der Wortlaut gleich geblieben ist.
Exit-Code 1, wenn Text weggefallen ist. Exit-Code 2, wenn es die Datei in REVISION nicht gibt oder REVISION
unbekannt ist.
"""
import difflib
import re
import subprocess
import sys
from pathlib import Path

from mdtext import plain
from projekt import ROOT

TOKEN = re.compile(r"\w(?:[\w.,/%–-]*\w)?|[^\w\s]")


def tokens(text):
    """(Wort, Zeilennummer) für jedes Wort und Satzzeichen. Backticks zählen nicht als Text."""
    out = []
    for n, line in enumerate(plain(text).replace("`", "").split("\n"), 1):
        out += [(t, n) for t in TOKEN.findall(line)]
    return out


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    path = Path(sys.argv[1]).resolve()
    rev = sys.argv[2] if len(sys.argv) == 3 else "HEAD"
    rel = path.relative_to(ROOT).as_posix()
    old_text = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{rel}"], capture_output=True, text=True)
    if old_text.returncode != 0:
        print(f"wortdiff: {rel} gibt es in {rev} nicht: {old_text.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    old, new = tokens(old_text.stdout), tokens(path.read_text(encoding="utf-8"))
    matcher = difflib.SequenceMatcher(None, [t for t, _ in old], [t for t, _ in new], autojunk=False)
    removed = 0
    for op, i1, i2, _, _ in matcher.get_opcodes():
        if op in ("delete", "replace"):
            removed += 1
            print(f"{rel}:{old[i1][1]}: weggefallen: {' '.join(t for t, _ in old[i1:i2])[:200]}")
    if removed:
        print(f"wortdiff: an {removed} Stelle(n) fehlt Text aus {rev}", file=sys.stderr)
        sys.exit(1)
    print(f"wortdiff: kein Text aus {rev} weggefallen")


if __name__ == "__main__":
    main()
