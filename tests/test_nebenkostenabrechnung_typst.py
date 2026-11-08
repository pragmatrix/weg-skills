"""Tests für die Typst-Vorlage `weg-vermieter-nebenkosten/nebenkostenabrechnung.typ`.

Sie halten fest, dass die Vorlage bei einer fehlenden Mindestangabe oder einer falschen Summe abbricht, dass ein
negatives Ergebnis „Ihr Guthaben“ heißt und dass ein Platzhalter mit `warnung` die Abrechnung als Entwurf markiert.
Alle Daten sind erfunden. Ohne `typst` werden die Tests übersprungen.
"""
import copy
import json
import shutil
import subprocess
import unittest

from _support import REPO

VORLAGE = REPO / "weg-vermieter-nebenkosten" / "nebenkostenabrechnung.typ"
HAT_TYPST = shutil.which("typst") is not None

DATEN = {
    "jahr": 2025,
    "vermieter": {"name": "Max Muster", "adresse": "Musterstraße 1, 12345 Musterstadt"},
    "mieterin": {
        "name": "Erika Beispiel",
        "adresse": "Beispielweg 2, 12345 Musterstadt",
        "wohnung": "EG links (Einheit 3, 250/1000 MEA)",
        "mietvertrag_vom": "2020-04-01",
    },
    "abrechnungszeitraum": {"von": "2025-01-01", "bis": "2025-12-31"},
    "datum_abrechnung": "2026-03-01",
    "verteilvermerk": "MEA sind die Miteigentumsanteile laut Teilungserklärung, Ihre Wohnung hat 250 von 1000.",
    "positionen": [
        {"position": "Allgemeinstrom", "betrag": 100.10, "gesamtkosten": 400.40, "schluessel": "MEA 250 von 1000",
         "betrkv": "§ 2 Nr. 11", "umlagefaehig": True, "fundstelle": "Abrechnung.pdf, S. 2"},
        {"position": "Müllgebühren", "betrag": 50.20, "gesamtkosten": 200.80, "schluessel": "MEA 250 von 1000",
         "betrkv": "§ 2 Nr. 8", "umlagefaehig": True, "berechnung": "200,80 € × 250/1000"},
    ],
    "summen": {"summe_betriebskosten": 150.30, "vorauszahlung": 120.00, "nachzahlung": 30.30},
}


def auswerten(daten, ausdruck):
    """Wertet `ausdruck` in der Vorlage mit `daten` aus. Ergebnis ist (Exit-Code, Ausgabe auf stdout und stderr)."""
    lauf = subprocess.run(
        ["typst", "eval", ausdruck, "--in", str(VORLAGE), "--input", "daten=" + json.dumps(daten)],
        capture_output=True, text=True,
    )
    return lauf.returncode, lauf.stdout + lauf.stderr


def wert(daten, label):
    code, ausgabe = auswerten(daten, f"query(<{label}>).first().value")
    if code != 0:
        raise AssertionError(ausgabe)
    return json.loads(ausgabe.strip().splitlines()[0])


@unittest.skipUnless(HAT_TYPST, "typst fehlt")
class NebenkostenabrechnungTest(unittest.TestCase):
    def daten(self):
        return copy.deepcopy(DATEN)

    def test_vollstaendige_daten_ergeben_nachzahlung_ohne_entwurf(self):
        self.assertEqual(wert(self.daten(), "ergebnis"), "Ihre Nachzahlung")
        self.assertFalse(wert(self.daten(), "entwurf"))

    def test_negatives_ergebnis_heisst_guthaben(self):
        d = self.daten()
        d["summen"].update(vorauszahlung=200.00, nachzahlung=-49.70)
        self.assertEqual(wert(d, "ergebnis"), "Ihr Guthaben")

    def test_warnung_markiert_entwurf(self):
        d = self.daten()
        d["positionen"][0]["warnung"] = "Platzhalter: Bescheid fehlt"
        self.assertTrue(wert(d, "entwurf"))

    def test_fehlende_mindestangaben_brechen_mit_allen_befunden_ab(self):
        d = self.daten()
        del d["positionen"][0]["schluessel"]
        del d["positionen"][1]["berechnung"]
        del d["verteilvermerk"]
        code, ausgabe = auswerten(d, "1")
        self.assertNotEqual(code, 0)
        self.assertIn("Position „Allgemeinstrom“ ohne schluessel", ausgabe)
        self.assertIn("Position „Müllgebühren“ ohne fundstelle oder berechnung", ausgabe)
        self.assertIn("verteilvermerk fehlt", ausgabe)

    def test_falsche_summe_bricht_ab(self):
        d = self.daten()
        d["summen"].update(summe_betriebskosten=150.31, nachzahlung=30.31)
        code, ausgabe = auswerten(d, "1")
        self.assertNotEqual(code, 0)
        self.assertIn("die Positionen ergeben 150,30", ausgabe)

    def test_nicht_umlagefaehige_position_zaehlt_nicht(self):
        d = self.daten()
        d["positionen"].append({"position": "Verwaltergebühr", "betrag": 99.0, "umlagefaehig": False})
        self.assertEqual(wert(d, "ergebnis"), "Ihre Nachzahlung")

    def test_anlage_ohne_pdf_datei_bricht_ab(self):
        d = self.daten()
        d["anlagen"] = [{"bezeichnung": "Heizkostenabrechnung", "datei": "Abrechnung.xlsx"}, {"datei": "a.pdf"}]
        code, ausgabe = auswerten(d, "1")
        self.assertNotEqual(code, 0)
        self.assertIn("Anlage „Heizkostenabrechnung“ ohne datei", ausgabe)
        self.assertIn("Anlage ohne bezeichnung", ausgabe)

    def test_steuer_35a_summiert_je_art(self):
        d = self.daten()
        d["positionen"][0]["steuer_35a"] = {"art": "handwerker", "betrag": 40.10, "berechnung": "Lohnanteil"}
        d["positionen"][1]["steuer_35a"] = {"art": "handwerker", "betrag": 10.00, "fundstelle": "Rechnung, S. 1"}
        self.assertEqual(wert(d, "steuer_35a"), {"handwerker": 5010})
        self.assertEqual(wert(self.daten(), "steuer_35a"), {})

    def test_steuer_35a_unplausibel_bricht_ab(self):
        d = self.daten()
        d["positionen"][0]["steuer_35a"] = {"art": "sonstig", "betrag": 100.11}
        code, ausgabe = auswerten(d, "1")
        self.assertNotEqual(code, 0)
        self.assertIn("steuer_35a.art ist weder", ausgabe)
        self.assertIn("steuer_35a.betrag ist größer als der Anteil des Mieters", ausgabe)
        self.assertIn("steuer_35a ohne fundstelle oder berechnung", ausgabe)

    def test_datum_im_abrechnungsjahr_bricht_ab(self):
        d = self.daten()
        d["datum_abrechnung"] = "2025-12-31"
        code, ausgabe = auswerten(d, "1")
        self.assertNotEqual(code, 0)
        self.assertIn("liegt nicht nach dem Abrechnungsjahr 2025", ausgabe)


if __name__ == "__main__":
    unittest.main()
