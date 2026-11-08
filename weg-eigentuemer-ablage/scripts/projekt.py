"""Projektordner der Ablage und die Regeln, welche Dateien die Skripte der WEG-Skills durchsuchen.

Der Projektordner ist das Wurzelverzeichnis des Git-Repositorys, in dem ein Ordner liegt. Liegt der Ordner in keinem
Repository, ist es der nächste Ordner auf dem Weg nach oben, in dem eine `justfile` und ein Hauptordner liegen. Die
`justfile` unterscheidet ihn von einem fremden Ordner, der zufällig etwa `Verwaltung/` enthält. So finden ihn auch
die Rezepte aus `ablage.just`, die mit `[no-cd]` im aktuellen Ordner laufen, etwa in `Abrechnungen/2025/`.

Ein Projektordner hat mindestens einen der Hauptordner aus dem Skill `weg-eigentuemer-ablage`. Fehlen alle, bricht
jedes Skript ab. So legt etwa `pdf2md.py` keine MDs in einem fremden Repository an, wenn es dort aufgerufen wird.

Skripte anderer Skills binden diese Datei über den Pfad des installierten Skills ein:

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "weg-eigentuemer-ablage" / "scripts"))
    from projekt import projektordner

`ROOT` ist der Projektordner des aktuellen Ordners. Er wird erst beim ersten Zugriff bestimmt. Ein Skript, das nur
`projektordner` mit einem eigenen Ordner aufruft, bricht deshalb nicht ab, wenn der aktuelle Ordner kein Projekt ist.
"""
from functools import cache
from pathlib import Path, PurePath
import hashlib
import subprocess
import sys
import unicodedata

HAUPTORDNER = ("Abrechnungen", "Versammlungen", "Verwaltung", "Stammdaten", "Vorgänge")

# Diese Ordner gehören nicht zur Ablage. Ausgenommen sind sie nur direkt im Projektordner. `tmp/` hält
# Zwischenstände, `Notizen/` eigene Beobachtungen und `scripts/` die Skripte des Projekts.
SKIP_DIRS = frozenset({"tmp", "Notizen", "scripts"})


def projektordner(start=".") -> Path:
    """Projektordner zu dem Ordner `start`. Ist er kein WEG-Projektordner, bricht das Skript ab."""
    out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode == 0:
        kandidaten = [Path(out.stdout.strip()).resolve()]
    else:
        start = Path(start).resolve()
        kandidaten = [p for p in (start, *start.parents) if (p / "justfile").is_file()] or [start]
    for root in kandidaten:
        if any((root / d).is_dir() for d in HAUPTORDNER):
            return root
    ohne_git = "" if out.returncode == 0 else "Er liegt in keinem Git-Repository und hat keine justfile, oder "
    sys.exit(f"{kandidaten[0]} ist kein WEG-Projektordner. {ohne_git}keiner der Ordner {', '.join(HAUPTORDNER)} "
             "ist da.")


@cache
def _root():
    return projektordner()


def __getattr__(name):
    if name == "ROOT":
        return _root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def skipped(rel: PurePath) -> bool:
    """Liegt der projektrelative Pfad außerhalb der Ablage?

    Das gilt für die Ordner aus `SKIP_DIRS` direkt im Projektordner. Es gilt auch für jeden Pfad, in dem ein
    versteckter Ordner vorkommt, etwa `.git/`, `.claude/` oder `.obsidian/`.
    """
    folders = rel.parts[:-1]
    return bool(folders) and (folders[0] in SKIP_DIRS or any(part.startswith(".") for part in folders))


def ignore_patterns(name: str) -> list[str]:
    """Muster aus der Ausnahmeliste `scripts/<name>` des Projekts, in Unicode-Form NFC.

    Leere Zeilen und Zeilen mit `#` am Anfang zählen nicht. Fehlt die Liste, gibt es keine Muster. Ein Pfad wird vor
    dem Vergleich ebenfalls nach NFC gewandelt (`nfc`). So passt ein Muster auch auf einen Namen, den das Dateisystem
    in der Form NFD speichert, etwa einen Namen mit Umlaut.
    """
    path = _root() / "scripts" / name
    if not path.exists():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [nfc(line) for line in lines if line and not line.startswith("#")]


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def sha256(path: Path) -> str:
    """SHA-256-Hash des Inhalts einer Datei, als Hex-Text."""
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
