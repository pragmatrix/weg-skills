"""Tests für `weg-vermieter-nebenkosten/verify_abrechnung_xlsx.py`. Sie halten fest, dass die Prüfung eine falsche
Summe, ein falsches Ergebnis und das Vorjahr im Titel erkennt.

Das Skript braucht openpyxl. Ohne das Paket werden die Tests übersprungen. Mit dem Paket laufen sie so:
    uv run --with openpyxl python -m unittest discover -s tests
"""
import importlib.util
import unittest
from datetime import datetime

from _support import Projekt

HAT_OPENPYXL = importlib.util.find_spec("openpyxl") is not None
SKRIPT = "weg-vermieter-nebenkosten/verify_abrechnung_xlsx.py"

# Datenbasis: Kosten 150,50, Vorauszahlung 120,00, also eine Nachzahlung von 30,50.
DATENBASIS = {
    "datum_abrechnung": "2026-03-15",
    "summen": {"vorauszahlung": 120.00},
    "positionen": [
        {"position": "Grundsteuer", "betrag": 100.00, "umlagefaehig": True, "betrkv": "§ 2 Nr. 1",
         "fundstelle": {"datei": "Abrechnungen/2025/Abrechnung.pdf", "seite": 2}},
        {"position": "Müllabfuhr", "betrag": 50.50, "umlagefaehig": True, "betrkv": "§ 2 Nr. 8",
         "berechnung": "Anteil 1/4 von 202,00"},
    ],
}


def abrechnung(jahr, summe="=SUM(F10:F11)", ergebnis="=F13-F14"):
    """Eine Abrechnung im Layout, das `nk_pfade.locate_rows` erwartet. Zeile 12 ist die Leerzeile über „Summe“."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws["A1"] = f"Nebenkostenabrechnung {jahr} Musterstraße 1, Einheit 3"
    ws["E6"], ws["F6"] = "Datum:", datetime(jahr + 1, 3, 15)
    ws["A8"] = f"Sehr geehrte Mieterin, hiermit erhalten Sie die Nebenkostenabrechnung für das Jahr {jahr}."
    ws["A10"], ws["F10"] = "Grundsteuer", 100.00
    ws["A11"], ws["F11"] = "Müllabfuhr", 50.50
    ws["A13"], ws["F13"] = "Summe", summe
    ws["A14"], ws["F14"] = "Ihre Vorauszahlung", 120.00
    ws["A15"], ws["F15"] = "Ihre Nachzahlung", ergebnis
    return wb


@unittest.skipUnless(HAT_OPENPYXL, "openpyxl fehlt")
class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)
        self.projekt.write("Vermietung/2025/nebenkostenabrechnung_2025_mustermann.json", DATENBASIS)
        (self.projekt.root / "Vermietung" / "2024").mkdir()
        abrechnung(2024).save(self.projekt.root / "Vermietung/2024/2024 Nebenkostenabrechnung.xlsx")

    def pruefe(self, wb):
        wb.save(self.projekt.root / "Vermietung/2025/2025 Nebenkostenabrechnung.xlsx")
        return self.projekt.run(SKRIPT, 2025)

    def test_richtige_abrechnung_besteht(self):
        # Dieser Fall zeigt, dass die Daten der anderen Tests bis auf ihren einen Fehler stimmen.
        ergebnis = self.pruefe(abrechnung(2025))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)

    def test_falscher_summenbereich(self):
        ergebnis = self.pruefe(abrechnung(2025, summe="=SUM(F10:F10)"))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("Summe", ergebnis.stdout)

    def test_falsche_formel_der_nachzahlung(self):
        ergebnis = self.pruefe(abrechnung(2025, ergebnis="=F13+F14"))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("Ergebnis", ergebnis.stdout)

    def test_vorjahr_im_titel(self):
        wb = abrechnung(2025)
        wb.active["A1"] = "Nebenkostenabrechnung 2025 Musterstraße 1, Zeitraum 2024"
        ergebnis = self.pruefe(wb)
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("Titel", ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
