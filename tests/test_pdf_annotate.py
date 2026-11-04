"""Tests für `report_items` in `pdf-annotate/pdf_annotate.py`. Sie halten fest, welche Punkte eines Prüfberichts das
Skript liest und welche Farbe sie bekommen.

Das Skript braucht PyMuPDF. Ohne das Paket werden die Tests übersprungen. Mit dem Paket laufen sie so:
    uv run --with pymupdf python -m unittest discover -s tests
"""
import importlib.util
import unittest

from _support import module

HAT_PYMUPDF = importlib.util.find_spec("pymupdf") is not None
SECTIONS = {"1": "Ergebnis", "2": "Fehler", "4": "Änderungswunsch"}

BERICHT = """\
## 1. Ergebnis

| Nr. | Prüfpunkt | Status | Befund | Beleg |
|---|---|---|---|---|
| 1.1 | Gesamtkosten | Abweichung | 12,00 € zu viel | |
| 1.2 | Rücklage | stimmt | | [Abr. S. 3](<a.pdf>) |

## 2. Fehler

| Nr. | TOP | Kurzinhalt | erwartete Umsetzung | Status | Beleg |
|---|---|---|---|---|---|
| 2.1 | 5 | Dachrinne | Auftrag 2025 | nicht prüfbar | fällig ab 01.03.2026 |

## 4. Änderungswunsch

- [ ] 4.1 Laufzeit kürzen
- 4.1.2 Kündigungsfrist nennen
"""


@unittest.skipUnless(HAT_PYMUPDF, "PyMuPDF fehlt")
class ReportItemsTest(unittest.TestCase):
    def setUp(self):
        self.items = module("pdf-annotate", "pdf_annotate").report_items(BERICHT, SECTIONS)

    def test_tabelle_mit_leerer_zelle(self):
        self.assertEqual(self.items["1.2"][0], "note")
        self.assertEqual(self.items["1.2"][1], "Ergebnis 1.2: Rücklage (stimmt). Beleg: Abr. S. 3.")

    def test_abweichung_ist_rot(self):
        self.assertEqual(self.items["1.1"][0], "important")

    def test_tabelle_mit_sechs_spalten(self):
        weight, text = self.items["2.1"]
        self.assertEqual(weight, "error")
        self.assertIn("(nicht prüfbar)", text)
        self.assertIn("Kurzinhalt: Dachrinne.", text)
        self.assertIn("Beleg: fällig ab 01.03.2026.", text)

    def test_checklistenpunkt_und_dreistufige_nummer(self):
        self.assertIn("Laufzeit kürzen", self.items["4.1"][1])
        self.assertIn("Kündigungsfrist nennen", self.items["4.1.2"][1])


if __name__ == "__main__":
    unittest.main()
