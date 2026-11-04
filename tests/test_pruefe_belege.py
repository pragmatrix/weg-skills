"""Tests für `weg-konten-belege/pruefe_belege.py`. Sie halten fest, wann die Datenbasis eines Jahres als geprüft gilt."""
import unittest

from _support import Projekt

SKRIPT = "weg-konten-belege/pruefe_belege.py"
ORDNER = "Abrechnungen/2025"
KONTO = "DE00 0000 0000 0000 0000 00"


def stand(betrag, vom):
    return {"betrag": betrag, "vom": vom}


def konto(endstand=1250.00):
    """Ein Konto mit einem Platzhalter für Auszug 1 und einem echten Auszug 2 mit einer Gutschrift über 250,00."""
    return {"jahr": 2025, "konten": [{
        "kontonummer": KONTO, "saldo_31_12_2024": 1000.00, "saldo_31_12_2025": endstand,
        "auszuege": [
            {"nr": "1/2025", "datei": None, "alter_kontostand": stand(1000.00, "2025-01-01"),
             "neuer_kontostand": stand(1000.00, "2025-06-30"), "transaktionen": []},
            {"nr": "2/2025", "datei": "x.pdf", "alter_kontostand": stand(1000.00, "2025-07-01"),
             "neuer_kontostand": stand(endstand, "2025-12-31"), "transaktionen": [
                 {"buchungstag": "2025-07-01", "wertstellung": "2025-07-01", "art": "Gutschrift",
                  "partner": "Max Mustermann", "betrag": 250.00, "soll_haben": "haben",
                  "verwendungszweck": "Hausgeld Musterstraße 1"}]}]}]}


def belege(*offene_punkte):
    return {"jahr": 2025, "belege": [], "offene_punkte": list(offene_punkte)}


DOKUMENTIERT = f"fehlt: Kontoauszug {KONTO} 1/2025 – beim Nutzer angefragt"


class PruefeBelegeTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)

    def pruefe(self, konto_json, belege_json):
        if konto_json is not None:
            self.projekt.write(f"{ORDNER}/konto_2025.json", konto_json)
        if belege_json is not None:
            self.projekt.write(f"{ORDNER}/belege_2025.json", belege_json)
        return self.projekt.run(SKRIPT, ORDNER)

    def test_dokumentierter_platzhalter_besteht(self):
        # Dieser Fall zeigt, dass die Daten der anderen Tests bis auf ihren einen Fehler stimmen.
        ergebnis = self.pruefe(konto(), belege(DOKUMENTIERT))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def test_fehlende_json_ist_ein_fehler(self):
        ergebnis = self.pruefe(konto(), None)
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("belege_*.json", ergebnis.stdout)

    def test_ein_cent_in_der_saldo_kette_ist_ein_fehler(self):
        falsch = konto(endstand=1250.01)
        ergebnis = self.pruefe(falsch, belege(DOKUMENTIERT))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)

    def test_platzhalter_ohne_offenen_punkt_ist_ein_fehler(self):
        ergebnis = self.pruefe(konto(), belege())
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn(f"fehlt: Kontoauszug {KONTO} 1/2025", ergebnis.stdout)

    def test_schluessel_mit_folgender_ziffer_dokumentiert_nicht(self):
        # „1/20251“ beginnt mit dem Schlüssel „1/2025“, benennt aber einen anderen Auszug.
        ergebnis = self.pruefe(konto(), belege(f"fehlt: Kontoauszug {KONTO} 1/20251 – anderer Auszug"))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
