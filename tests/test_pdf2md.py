"""Tests für die Aktualität der Text-MDs in `weg-eigentuemer-ablage/scripts/pdf2md.py`.

Eine MD gilt als aktuell, wenn der Hash in ihrer Markierung zum PDF passt. Nach `git clone` sind die Dateizeiten
beliebig. Der Test hält fest, dass `--check` dann trotzdem jede MD als aktuell ansieht. Ohne Poppler wird er
übersprungen.
"""
import os
import shutil
import time
import unittest

from _support import Projekt, git, pdf

SKRIPT = "weg-eigentuemer-ablage/scripts/pdf2md.py"
HAT_POPPLER = all(shutil.which(t) for t in ("pdftotext", "pdfinfo"))


@unittest.skipUnless(HAT_POPPLER, "Poppler fehlt")
class FrischeTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)
        for name in ("Abrechnung 2025", "Wirtschaftsplan 2026"):
            (self.projekt.root / "Abrechnungen" / f"{name}.pdf").write_bytes(pdf(f"{name} Musterstrasse 1 Seite eins"))
        erzeugt = self.projekt.run(SKRIPT)
        self.assertEqual(erzeugt.returncode, 0, erzeugt.stdout + erzeugt.stderr)
        git(self.projekt.root, "add", "-A")
        git(self.projekt.root, "commit", "-qm", "Ablage")

    def test_nach_clone_mit_neueren_pdfs_ist_jede_md_aktuell(self):
        klon = self.projekt.root.parent / "klon"
        git(self.projekt.root.parent, "clone", "-q", str(self.projekt.root), str(klon))
        # Die PDFs bekommen eine spätere Zeit als ihre MDs. Nach dem alten Vergleich der Dateizeiten fehlte so jede MD.
        spaeter = time.time() + 60
        for p in (klon / "Abrechnungen").glob("*.pdf"):
            os.utime(p, (spaeter, spaeter))
        ergebnis = self.projekt.run(SKRIPT, "--check", cwd=klon)
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)

    def test_geaendertes_pdf_ist_veraltet(self):
        (self.projekt.root / "Abrechnungen" / "Abrechnung 2025.pdf").write_bytes(pdf("Abrechnung 2025 zweite Fassung"))
        ergebnis = self.projekt.run(SKRIPT, "--check")
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("veraltet", ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
