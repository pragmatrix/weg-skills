"""Tests für `weg-konten-belege/korrelation_zahlungen.py` und die Lücken aus `luecken.py`.

Sie halten fest, welche Bankbuchung als Zahlung des Eigentümers zählt und wann eine Lücke als dokumentiert gilt.
"""
import unittest

from _support import Projekt, module

korrelation = module("weg-konten-belege", "korrelation_zahlungen")
SKRIPT = "weg-konten-belege/korrelation_zahlungen.py"
ORDNER = "Abrechnungen/2025"


class NamensWoerterTest(unittest.TestCase):
    def passt(self, eigentuemer, partner):
        return korrelation.namens_woerter(eigentuemer) <= korrelation.namens_woerter(partner)

    def test_schreibweisen_der_bank_passen(self):
        self.assertTrue(self.passt("Müller, Hans", "HANS MUELLER"))
        self.assertTrue(self.passt("Müller, Hans", "Dr. Hans Müller"))

    def test_anderer_vorname_passt_nicht(self):
        self.assertFalse(self.passt("Müller, Hans", "Erika Müller"))

    def test_name_als_teil_eines_anderen_namens_passt_nicht(self):
        self.assertFalse(self.passt("Ott", "Gottschalk"))


def zahlung(datum):
    return {"datum": datum, "betrag": 250.00, "bewirtschaftung": 200.00, "ruecklage": 50.00}


def stand(betrag, vom):
    return {"betrag": betrag, "vom": vom}


# Auszug 1 fehlt und deckt das erste Halbjahr ab. Auszug 2 enthält nur die Zahlung vom 1. Juli.
KONTO = {"jahr": 2025, "konten": [{
    "kontonummer": "DE00 0000 0000 0000 0000 00", "saldo_31_12_2024": 1000.00, "saldo_31_12_2025": 1250.00,
    "auszuege": [
        {"nr": "1/2025", "datei": None, "alter_kontostand": stand(1000.00, "2025-01-01"),
         "neuer_kontostand": stand(1000.00, "2025-06-30"), "transaktionen": []},
        {"nr": "2/2025", "datei": "x.pdf", "alter_kontostand": stand(1000.00, "2025-07-01"),
         "neuer_kontostand": stand(1250.00, "2025-12-31"), "transaktionen": [
             {"buchungstag": "2025-07-01", "wertstellung": "2025-07-01", "art": "Gutschrift",
              "partner": "MUELLER HANS", "betrag": 250.00, "soll_haben": "haben", "verwendungszweck": "Hausgeld"}]}]}]}


def abrechnung(*offene_punkte):
    """Drei Zahlungen: eine im fehlenden Auszug, eine belegte und eine ohne Bankbuchung."""
    return {"einheit": {"eigentuemer": "Müller, Hans", "nummer": 3},
            "abrechnungszeitraum": {"von": "2025-01-01", "bis": "2025-12-31"},
            "zahlungen": {"liste": [zahlung("2025-02-01"), zahlung("2025-07-01"), zahlung("2025-08-01")]},
            "offene_punkte": list(offene_punkte)}


class LueckenTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)
        self.projekt.write(f"{ORDNER}/konto_2025.json", KONTO)

    def korreliere(self, abrechnung_json):
        self.projekt.write(f"{ORDNER}/weg_abrechnung_2025_we3.json", abrechnung_json)
        return self.projekt.run(SKRIPT, f"{ORDNER}/weg_abrechnung_2025_we3.json", f"{ORDNER}/konto_2025.json")

    def test_undokumentierte_luecken_ergeben_exit_1(self):
        ergebnis = self.korreliere(abrechnung())
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("unverifizierbar: Zahlung 2025-02-01 250,00", ergebnis.stdout)
        self.assertIn("fehlt: Zahlung 2025-08-01 250,00", ergebnis.stdout)

    def test_dokumentierte_luecken_ergeben_exit_0(self):
        ergebnis = self.korreliere(abrechnung(
            "unverifizierbar: Zahlung 2025-02-01 250,00 – Auszug fehlt",
            "fehlt: Zahlung 2025-08-01 250,00 – Sammel-Lastschrift, in der Buchungsliste belegt"))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def test_eine_offene_luecke_genuegt_fuer_exit_1(self):
        ergebnis = self.korreliere(abrechnung("unverifizierbar: Zahlung 2025-02-01 250,00 – Auszug fehlt"))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
