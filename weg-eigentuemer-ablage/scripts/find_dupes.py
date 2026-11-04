#!/usr/bin/env python3
"""Findet Dateien mit gleichem Inhalt (byte-gleiche Dubletten).

Aufruf (im Projektordner, siehe `projekt.py`):
    python3 find_dupes.py              ganze Ablage prüfen, Exit-Code 1 bei Dubletten
    python3 find_dupes.py DATEI…       zu jeder Datei die gleichen Dateien in der Ablage nennen

Die zweite Form ist für neue Dateien vor dem Ablegen gedacht, etwa Downloads aus dem Portal. Die Dateien dürfen
außerhalb des Projektordners liegen. Sie meldet nur und endet immer mit Exit-Code 0.

Verglichen werden alle Dateien außer Markdown. Text-MDs sind aus ihrem PDF erzeugt und wären sonst doppelt gemeldet.
Ausgenommen sind die Ordner `tmp/`, `Notizen/`, `.git/` und `.claude/` sowie Dateien, die auf ein Muster in
`scripts/dupes-ignore.txt` passen. Dort stehen gewollte Kopien, etwa die Anlagen eines Anschreibens.
"""
from pathlib import Path
import argparse
import fnmatch
import hashlib
import sys
import unicodedata

from projekt import ROOT

SKIP_DIRS = {"tmp", "Notizen", ".git", ".claude", "__pycache__"}
SKIP_NAMES = {".DS_Store"}
IGNORE_FILE = ROOT / "scripts" / "dupes-ignore.txt"


def ignore_patterns():
    if not IGNORE_FILE.exists():
        return []
    lines = (l.strip() for l in IGNORE_FILE.read_text(encoding="utf-8").splitlines())
    return [unicodedata.normalize("NFC", l) for l in lines if l and not l.startswith("#")]


def files(patterns):
    """Alle Dateien der Ablage, die verglichen werden, als Pfade relativ zum Projektordner."""
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or path.name in SKIP_NAMES or path.suffix.lower() == ".md":
            continue
        if path.is_symlink() or not path.is_file():
            continue
        name = unicodedata.normalize("NFC", rel.as_posix())
        if any(fnmatch.fnmatch(name, pat) for pat in patterns):
            continue
        yield rel


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def groups(paths):
    """Gruppen gleichen Inhalts. Erst nach Größe, dann nur bei gleicher Größe nach Prüfsumme."""
    by_size = {}
    for rel in paths:
        by_size.setdefault((ROOT / rel).stat().st_size, []).append(rel)
    by_hash = {}
    for same_size in by_size.values():
        if len(same_size) > 1:
            for rel in same_size:
                by_hash.setdefault(digest(ROOT / rel), []).append(rel)
    return [sorted(g) for g in by_hash.values() if len(g) > 1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dateien", nargs="*", type=Path)
    args = ap.parse_args()
    patterns = ignore_patterns()

    if args.dateien:
        index = {}
        for rel in files(patterns):
            index.setdefault((ROOT / rel).stat().st_size, []).append(rel)
        for new in args.dateien:
            want = digest(new)
            same = [rel for rel in index.get(new.stat().st_size, []) if digest(ROOT / rel) == want]
            same = [rel for rel in same if (ROOT / rel).resolve() != new.resolve()]
            print(f"{new}: " + (", ".join(r.as_posix() for r in same) if same else "neu"))
        return 0

    found = groups(files(patterns))
    for g in found:
        print("Dublette: " + " = ".join(r.as_posix() for r in g))
    if found:
        print(f"find_dupes: {len(found)} Gruppe(n). Eine Datei löschen oder die Kopie in scripts/dupes-ignore.txt eintragen.")
        return 1
    print("find_dupes: keine Dubletten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
