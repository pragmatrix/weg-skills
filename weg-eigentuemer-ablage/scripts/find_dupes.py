#!/usr/bin/env python3
"""Findet Dateien mit gleichem Inhalt (byte-gleiche Dubletten).

Aufruf (im Projektordner, siehe `projekt.py`):
    python3 find_dupes.py              ganze Ablage prüfen, Exit-Code 1 bei Dubletten
    python3 find_dupes.py DATEI…       zu jeder Datei die gleichen Dateien in der Ablage nennen

Die zweite Form ist für neue Dateien vor dem Ablegen gedacht, etwa Downloads aus dem Portal. Die Dateien dürfen
außerhalb des Projektordners liegen. Sie meldet nur und endet immer mit Exit-Code 0.

Verglichen werden alle Dateien außer Markdown. Text-MDs sind aus ihrem PDF erzeugt und wären sonst doppelt gemeldet.
Leere Dateien zählen nicht, weil sie alle denselben Inhalt haben, etwa zwei `.gitkeep`. Ausgenommen sind außerdem
die Ordner außerhalb der Ablage und Dateien, die auf ein Muster in `scripts/dupes-ignore.txt` passen. Außerhalb der
Ablage liegen die Ordner `tmp/`, `Notizen/` und `scripts/` direkt im Projektordner und jeder versteckte Ordner wie
`.git/` oder `.obsidian/` (`projekt.skipped`). In `dupes-ignore.txt` stehen gewollte Kopien, etwa die Anlagen eines
Anschreibens.
"""
from pathlib import Path
import argparse
import fnmatch
import sys

import projekt
from projekt import ROOT, nfc, sha256, skipped

SKIP_NAMES = {".DS_Store"}


def ignore_patterns():
    """Muster der gewollten Kopien aus `scripts/dupes-ignore.txt`.

    Die Funktion bleibt in diesem Modul, weil `etg24_abgleich.py` im Skill `etg24-portal` sie von hier importiert.
    """
    return projekt.ignore_patterns("dupes-ignore.txt")


def files(patterns):
    """Alle nicht leeren Dateien der Ablage, die verglichen werden, als Pfade relativ zum Projektordner."""
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if skipped(rel) or path.name in SKIP_NAMES or path.suffix.lower() == ".md":
            continue
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            continue
        if any(fnmatch.fnmatch(nfc(rel.as_posix()), pat) for pat in patterns):
            continue
        yield rel


def groups(paths):
    """Gruppen gleichen Inhalts. Erst nach Größe, dann nur bei gleicher Größe nach Prüfsumme."""
    by_size = {}
    for rel in paths:
        by_size.setdefault((ROOT / rel).stat().st_size, []).append(rel)
    by_hash = {}
    for same_size in by_size.values():
        if len(same_size) > 1:
            for rel in same_size:
                by_hash.setdefault(sha256(ROOT / rel), []).append(rel)
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
            want = sha256(new)
            same = [rel for rel in index.get(new.stat().st_size, []) if sha256(ROOT / rel) == want]
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
