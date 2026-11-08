"""Tests für `weg-konten-belege/pruefe_belege.py`. Sie halten fest, wann die Datenbasis eines Jahres als geprüft gilt."""
import unittest

from _support import KONTONUMMER as KONTO, Projekt, auszug, buchung
from _support import konto as konto_json

SKRIPT = "weg-konten-belege/pruefe_belege.py"
ORDNER = "Abrechnungen/2025"


def konto(endstand=1250.00):
    """Ein Konto mit einem Platzhalter für Auszug 1 und einem echten Auszug 2 mit einer Gutschrift über 250,00."""
    return konto_json(
        1000.00, endstand,
        auszug("1/2025", 1000.00, 1000.00, "2025-01-01", "2025-06-30", datei=None),
        auszug("2/2025", 1000.00, endstand, "2025-07-01", "2025-12-31",
               buchung("2025-07-01", "Max Mustermann", 250.00, verwendungszweck="Hausgeld Musterstraße 1")))


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
