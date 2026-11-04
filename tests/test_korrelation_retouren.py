"""Tests für Durchgang 2 von `weg-konten-belege/korrelation_zahlungen.py`, den Beleg einer Lastschrift durch ihre
Retoure.

Zieht die Verwaltung das Hausgeld per Sammel-Lastschrift ein, steht die Zahlung X nicht einzeln im Kontoauszug. Platzt
sie, bucht die Bank eine Retoure über −(X + Entgelt), deren Verwendungszweck „Hausgeld X“ nennt. Die Abrechnung führt
dann die Zahlung +X und eine Gegenbuchung −(X + Entgelt). Die Retoure belegt X, wenn das Entgelt über 0 und höchstens
`ENTGELT_MAX` liegt, die Gegenbuchung höchstens 2 Tage neben der Zahlung steht und die Retoure höchstens 7 Tage
neben der Zahlung gebucht ist.
"""
import unittest

from _support import Projekt

SKRIPT = "weg-konten-belege/korrelation_zahlungen.py"
ORDNER = "Abrechnungen/2025"
ZAHLUNG = "2025-03-03"


def konto(retoure_datum, retoure_betrag=253.00):
    """Ein Auszug für das ganze Jahr. Er enthält nur die Retoure."""
    stand = lambda b, vom: {"betrag": b, "vom": vom}
    entgelt = f"{retoure_betrag - 250:.2f}".replace(".", ",")
    return {"jahr": 2025, "konten": [{
        "kontonummer": "DE00 0000 0000 0000 0000 00", "saldo_31_12_2024": 1000.00, "saldo_31_12_2025": 747.00,
        "auszuege": [{"nr": "1/2025", "datei": "x.pdf", "alter_kontostand": stand(1000.00, "2025-01-01"),
                      "neuer_kontostand": stand(747.00, "2025-12-31"), "transaktionen": [
                          {"buchungstag": retoure_datum, "wertstellung": retoure_datum, "art": "Retoure",
                           "partner": "Hans Müller", "betrag": retoure_betrag, "soll_haben": "soll",
                           "verwendungszweck": f"Rücklastschrift Hausgeld 250,00 + Entgelt {entgelt}"}]}]}]}


def abrechnung(gegenbuchung_datum, gegenbuchung_betrag=-253.00):
    """Die Zahlung von 250,00 am 3. März und ihre Gegenbuchung nach der geplatzten Lastschrift."""
    buchung = lambda datum, betrag: {"datum": datum, "betrag": betrag, "bewirtschaftung": betrag, "ruecklage": 0.0}
    return {"einheit": {"eigentuemer": "Müller, Hans", "nummer": 3},
            "abrechnungszeitraum": {"von": "2025-01-01", "bis": "2025-12-31"},
            "zahlungen": {"liste": [buchung(ZAHLUNG, 250.00), buchung(gegenbuchung_datum, gegenbuchung_betrag)]},
            "offene_punkte": []}


class RetourenTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)

    def korreliere(self, konto_json, abrechnung_json):
        self.projekt.write(f"{ORDNER}/konto_2025.json", konto_json)
        self.projekt.write(f"{ORDNER}/weg_abrechnung_2025_we3.json", abrechnung_json)
        return self.projekt.run(SKRIPT, f"{ORDNER}/weg_abrechnung_2025_we3.json", f"{ORDNER}/konto_2025.json")

    def assertIndirekt(self, ergebnis):
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)
        self.assertIn("INDIREKT", ergebnis.stdout)

    def assertZahlungFehlt(self, ergebnis):
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertNotIn("INDIREKT", ergebnis.stdout)
        self.assertIn(f"fehlt: Zahlung {ZAHLUNG} 250,00", ergebnis.stdout)

    def test_retoure_belegt_die_zahlung(self):
        # Die Retoure liegt 4 Tage neben der Gegenbuchung, zu weit für Durchgang 1. Erst Durchgang 2 ordnet sie zu.
        ergebnis = self.korreliere(konto("2025-03-08"), abrechnung("2025-03-04"))
        self.assertIndirekt(ergebnis)
        self.assertIn("OK               Retoure 1/2025 vom 2025-03-08", ergebnis.stdout)

    def test_entgelt_ueber_dem_hoechstwert(self):
        ergebnis = self.korreliere(konto("2025-03-08", 261.00), abrechnung("2025-03-04", -261.00))
        self.assertZahlungFehlt(ergebnis)

    def test_gegenbuchung_mehr_als_zwei_tage_neben_der_zahlung(self):
        self.assertZahlungFehlt(self.korreliere(konto("2025-03-08"), abrechnung("2025-03-06")))

    def test_retoure_mehr_als_sieben_tage_neben_der_zahlung(self):
        self.assertZahlungFehlt(self.korreliere(konto("2025-03-11"), abrechnung("2025-03-04")))

    def test_in_durchgang_1_verbrauchte_retoure_belegt_trotzdem(self):
        # Die Retoure liegt einen Tag neben der Gegenbuchung. Durchgang 1 ordnet sie ihr deshalb schon exakt zu.
        ergebnis = self.korreliere(konto("2025-03-05"), abrechnung("2025-03-04"))
        self.assertIndirekt(ergebnis)
        self.assertIn("OK               Bank 1/2025", ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
