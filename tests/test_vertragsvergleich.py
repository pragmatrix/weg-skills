"""Tests für `weg-abrechnung-pruefen/vertragsvergleich.py`. Sie prüfen die Textfunktionen ohne PDF.

Eine Fassung ist hier eine Liste von Seiten, jede eine Liste ihrer Zeilen, so wie `pages` sie aus `pdftotext` liest.
"""
import unittest

from _support import module

vv = module("weg-abrechnung-pruefen", "vertragsvergleich")


def seite(nr, zelle):
    """Eine Seite mit Kopfzeile, Fußzeile und der Tabellenzelle `zelle` mitten auf der Seite."""
    return ["Verwaltervertrag Musterstraße 1", "Anlage Leistungsverzeichnis", f"Abschnitt {nr}.",
            f"Leistung {nr} der Verwaltung.", zelle, f"Hinweis {nr} zur Leistung.", "Erste Zeile des Endes.",
            "Musterverwaltung GmbH", "Stand 01/2026"]


class KopfFussTest(unittest.TestCase):
    def test_kurze_zelle_mitten_auf_vielen_seiten_bleibt(self):
        alt = [seite(n, "inklusive") for n in range(1, 5)]
        neu = alt[:2] + [seite(3, "gesondert")] + alt[3:]
        rand = vv.kopf_fuss(alt, neu)
        self.assertIn("Verwaltervertrag Musterstraße 1", rand)
        self.assertNotIn("inklusive", rand)
        self.assertIn("inklusive", " ".join(vv.sentences(alt, rand)))
        self.assertIn("gesondert", " ".join(vv.sentences(neu, rand)))
        self.assertNotIn("Musterverwaltung GmbH", " ".join(vv.sentences(neu, rand)))


class EntsilbenTest(unittest.TestCase):
    def test_ergaenzungsstrich_bleibt(self):
        text = " ".join(vv.sentences([["Grund-", "und besondere Leistungen."]], set()))
        self.assertEqual(text, "Grund- und besondere Leistungen.")

    def test_silbentrennung_am_zeilenende_wird_aufgehoben(self):
        self.assertEqual(vv.entsilben(["die Koordi-", "nierung der Handwerker"]), ["die Koordinierung der Handwerker"])


if __name__ == "__main__":
    unittest.main()
