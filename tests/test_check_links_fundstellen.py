"""Tests für die Fundstellen in Links auf PDFs, geprüft von `weg-eigentuemer-ablage/scripts/check_links.py`.

Die Seite aus Linktext oder Tooltip muss es im PDF geben, und jedes Zitat im Tooltip muss auf dieser Seite stehen. Das
Skript liest die Seiten aus der Text-MD neben dem PDF. Findet es ein Zitat dort nicht, liest es die Seite mit
`pdftotext`. Ohne Poppler werden die Tests deshalb übersprungen.
"""
import shutil
import unittest

from _support import Projekt, pdf

SKRIPT = "weg-eigentuemer-ablage/scripts/check_links.py"
HAT_POPPLER = all(shutil.which(t) for t in ("pdftotext", "pdfinfo"))

# Die Text-MD hat zwei Seiten. Auf Seite 2 ist „Erhaltungsrücklage“ am Zeilenende getrennt.
TEXT_MD = """\
<!-- generiert von scripts/pdf2md.py aus Abrechnung 2025.pdf -->
# Abrechnung 2025

## Seite 1

Die Gesamtkosten der Gemeinschaft betragen im Jahr 2025
insgesamt 12.345,00 Euro.

## Seite 2

Die Erhaltungs-
rücklage beträgt zum Jahresende 5.000,00 Euro.
"""


@unittest.skipUnless(HAT_POPPLER, "Poppler fehlt")
class FundstellenTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)
        (self.projekt.root / "Abrechnungen" / "Abrechnung 2025.pdf").write_bytes(pdf("Abrechnung 2025 Musterstrasse 1"))
        self.projekt.write("Abrechnungen/Abrechnung 2025.md", TEXT_MD)

    def pruefe(self, seite, zitat):
        """Prüft einen Link auf die Abrechnung mit der Seitenangabe `seite` und dem Tooltip-Zitat `zitat`."""
        self.projekt.write("Abrechnungen/README.md", f'[Abr. 2025, {seite}](<Abrechnung 2025.pdf> "{zitat}")\n')
        return self.projekt.run(SKRIPT)

    def assertBesteht(self, ergebnis):
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def assertMeldet(self, ergebnis, meldung):
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn(meldung, ergebnis.stdout)

    def test_zitat_auf_der_genannten_seite(self):
        self.assertBesteht(self.pruefe("S. 1", "„Gesamtkosten der Gemeinschaft betragen“"))

    def test_absteigender_bereich_ist_ungueltig(self):
        self.assertMeldet(self.pruefe("S. 2–1", "„Gesamtkosten der Gemeinschaft“"), "keine gültige Seitenangabe")
        self.assertMeldet(self.pruefe("S. 2–1 und 1", "„Gesamtkosten der Gemeinschaft“"), "keine gültige Seitenangabe")

    def test_seite_nach_der_letzten(self):
        self.assertMeldet(self.pruefe("S. 3", "„Gesamtkosten der Gemeinschaft“"), "S. 3 gibt es nicht")

    def test_zitat_auf_einer_anderen_seite(self):
        self.assertMeldet(self.pruefe("S. 2", "„Gesamtkosten der Gemeinschaft“"), "steht nicht auf S. 2")

    def test_teilstuecke_werden_einzeln_gesucht(self):
        self.assertBesteht(self.pruefe("S. 1", "„Gesamtkosten der Gemeinschaft … insgesamt 12.345,00 Euro“"))

    def test_jedes_teilstueck_muss_stehen(self):
        ergebnis = self.pruefe("S. 1", "„Gesamtkosten der Gemeinschaft … Rücklage für das Dach“")
        self.assertMeldet(ergebnis, "Zitat „Rücklage für das Dach“ steht nicht auf S. 1")


if __name__ == "__main__":
    unittest.main()
