"""Gemeinsame Hilfen der Tests: der Ort der Skills, ein synthetischer Projektordner und der Aufruf der Skripte.

Alle Daten der Tests sind erfunden. Ein Projektordner der Tests ist ein Git-Repository mit dem Hauptordner
`Abrechnungen/`, denn `projekt.projektordner` bricht ohne einen Hauptordner ab.
"""
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def module(skill_dir, name):
    """Importiert das Modul `name` aus dem Ordner `skill_dir` des Repositorys, etwa ("weg-konten-belege", "luecken")."""
    folder = str(REPO / skill_dir)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return importlib.import_module(name)


class Projekt:
    """Ein leerer Projektordner in einem temporären Ordner. Er wird mit `close` gelöscht."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "projekt"
        (self.root / "Abrechnungen").mkdir(parents=True)
        git(self.root, "init", "-q")

    def close(self):
        self._tmp.cleanup()

    def write(self, rel, content):
        """Schreibt eine Datei. Ein `dict` oder eine `list` wird als JSON geschrieben, alles andere als Text."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False, indent=1)
        path.write_text(content, encoding="utf-8")
        return path

    def run(self, script, *args, cwd=None):
        """Ruft ein Skript des Repositorys mit dem laufenden Python im Projektordner auf."""
        return subprocess.run([sys.executable, str(REPO / script), *map(str, args)], cwd=cwd or self.root,
                              capture_output=True, text=True)


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args], cwd=cwd,
                   check=True, capture_output=True)


def pdf(text):
    """Ein einseitiges PDF mit einer Zeile Text in Helvetica, ohne Bibliothek gebaut. Der Text ist ASCII."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objekte = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    daten, offsets = b"%PDF-1.4\n", []
    for n, obj in enumerate(objekte, 1):
        offsets.append(len(daten))
        daten += b"%d 0 obj\n" % n + obj + b"\nendobj\n"
    xref = len(daten)
    daten += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objekte) + 1)
    daten += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    daten += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objekte) + 1, xref)
    return daten
