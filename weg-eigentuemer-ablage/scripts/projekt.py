"""Projektordner der Ablage, für alle Skripte der WEG-Skills.

Der Projektordner ist das Wurzelverzeichnis des Git-Repositorys, in dem der aktuelle Ordner liegt. Liegt der aktuelle
Ordner in keinem Repository, ist er selbst der Projektordner. Die Rezepte aus `ablage.just` laufen im Ordner der
`justfile` des Projekts und finden ihn deshalb immer.

Ein Projektordner hat mindestens einen der Hauptordner aus dem Skill `weg-eigentuemer-ablage`. Fehlen alle, bricht
jedes Skript ab. So legt etwa `pdf2md.py` keine MDs in einem fremden Repository an, wenn es dort aufgerufen wird.
"""
from pathlib import Path
import subprocess
import sys

HAUPTORDNER = ("Abrechnungen", "Versammlungen", "Verwaltung", "Stammdaten", "Vorgänge")


def _root():
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = Path(out.stdout.strip() if out.returncode == 0 else ".").resolve()
    if not any((root / d).is_dir() for d in HAUPTORDNER):
        sys.exit(f"{root} ist kein WEG-Projektordner: keiner der Ordner {', '.join(HAUPTORDNER)} ist da.")
    return root


ROOT = _root()
