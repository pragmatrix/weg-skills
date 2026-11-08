"""Tests für `projekt.skipped` in `weg-eigentuemer-ablage/scripts/projekt.py`.

Jedes Prüfskript der Ablage überspringt die Pfade, für die `skipped` wahr ist. Die Regel ist ungleich: `tmp/`,
`Notizen/` und `scripts/` gelten nur direkt im Projektordner als außerhalb der Ablage, versteckte Ordner in jeder
Tiefe. Eine Datei direkt im Projektordner gehört immer zur Ablage, auch wenn ihr Name mit einem Punkt beginnt.
"""
from pathlib import PurePath
import unittest

from _support import module

projekt = module("weg-eigentuemer-ablage/scripts", "projekt")


class SkippedTest(unittest.TestCase):
    def test_ordner_ausserhalb_der_ablage(self):
        faelle = {
            "tmp/a.pdf": True,
            "Notizen/a.md": True,
            "Vorgänge/X/tmp/a.pdf": False,
            "Vorgänge/X/scripts/a.md": False,
            "Vorgänge/.obsidian/a.md": True,
            ".git/config": True,
            ".gitignore": False,
            "Abrechnungen/2025/a.pdf": False,
        }
        for pfad, erwartet in faelle.items():
            with self.subTest(pfad=pfad):
                self.assertEqual(projekt.skipped(PurePath(pfad)), erwartet)


if __name__ == "__main__":
    unittest.main()
