"""Tests für `weg-konten-belege/korrelation_zahlungen.py` und die Lücken aus `luecken.py`.

Sie halten fest, welche Bankbuchung als Zahlung des Eigentümers zählt, welcher Eingang in der Bank eine Lücke der
Abrechnung ist und wann eine Lücke als dokumentiert gilt.
"""
import unittest

from _support import Projekt, auszug, buchung, konto, module

korrelation = module("weg-konten-belege", "korrelation_zahlungen")
luecken = module("weg-konten-belege", "luecken")
SKRIPT = "weg-konten-belege/korrelation_zahlungen.py"
ORDNER = "Abrechnungen/2025"


class NamenTest(unittest.TestCase):
    def passt(self, eigentuemer, partner):
        return korrelation.passt(korrelation.eigentuemer_namen(eigentuemer), partner)

    def test_schreibweisen_der_bank_passen(self):
        self.assertTrue(self.passt("Müller, Hans", "HANS MUELLER"))
        self.assertTrue(self.passt("Müller, Hans", "Dr. Hans Müller"))
        self.assertTrue(self.passt("René Weiß", "RENE WEISS"))
        self.assertTrue(self.passt("Hans-Peter Müller", "HANS PETER MUELLER"))

    def test_jeder_miteigentuemer_passt_mit_vollem_namen(self):
        self.assertTrue(self.passt("Hans und Erika Müller", "MUELLER HANS"))
        self.assertTrue(self.passt("Hans Peter und Erika Müller", "HANS PETER MUELLER"))
        self.assertTrue(self.passt("Müller, Hans und Erika", "Erika Müller"))
        self.assertTrue(self.passt("Hans Müller; Erika Schmidt", "SCHMIDT ERIKA"))

    def test_anderer_vorname_passt_nicht(self):
        self.assertFalse(self.passt("Müller, Hans", "Erika Müller"))
        self.assertFalse(self.passt("Hans-Peter Müller", "Peter Müller"))
        self.assertFalse(self.passt("Hans Peter und Erika Müller", "Hans Peter Schmidt"))

    def test_name_als_teil_eines_anderen_namens_passt_nicht(self):
        self.assertFalse(self.passt("Ott", "Gottschalk"))


class DokumentiertTest(unittest.TestCase):
    def test_schluessel_muss_am_anfang_stehen(self):
        schluessel = "fehlt: Zahlung 2025-08-01 250,00"
        self.assertTrue(luecken.dokumentiert(schluessel, [f"{schluessel} – Sammel-Lastschrift"]))
        self.assertFalse(luecken.dokumentiert(schluessel, [f"Nachfrage: {schluessel}"]))


def zahlung(datum, betrag=250.00):
    return {"datum": datum, "betrag": betrag, "bewirtschaftung": betrag, "ruecklage": 0.0}


def abrechnung(zahlungen, *offene_punkte, eigentuemer="Müller, Hans", einheit=3, vorjahre=0.0):
    return {"einheit": {"eigentuemer": eigentuemer, "nummer": einheit},
            "abrechnungszeitraum": {"von": "2025-01-01", "bis": "2025-12-31"},
            "vorjahre": {"abrechnungsergebnis": vorjahre, "zahlungseingang": vorjahre, "saldo": 0.0},
            "zahlungen": {"liste": zahlungen}, "offene_punkte": list(offene_punkte)}


class Korrelation(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)

    def korreliere(self, konto_json, abrechnung_json, **weitere):
        """Korreliert Einheit 3. `weitere` legt weitere Abrechnungen als we<N> in denselben Ordner."""
        self.projekt.write(f"{ORDNER}/konto_2025.json", konto_json)
        self.projekt.write(f"{ORDNER}/weg_abrechnung_2025_we3.json", abrechnung_json)
        for name, inhalt in weitere.items():
            self.projekt.write(f"{ORDNER}/weg_abrechnung_2025_{name}.json", inhalt)
        return self.projekt.run(SKRIPT, f"{ORDNER}/weg_abrechnung_2025_we3.json", f"{ORDNER}/konto_2025.json")


# Auszug 1 fehlt und deckt das erste Halbjahr ab. Auszug 2 enthält nur die Zahlung vom 1. Juli.
KONTO_MIT_LUECKE = konto(1000.00, 1250.00,
                         auszug("1/2025", 1000.00, 1000.00, "2025-01-01", "2025-06-30", datei=None),
                         auszug("2/2025", 1000.00, 1250.00, "2025-07-01", "2025-12-31",
                                buchung("2025-07-01", "MUELLER HANS", 250.00)))
# Drei Zahlungen: eine im fehlenden Auszug, eine belegte und eine ohne Bankbuchung.
DREI_ZAHLUNGEN = [zahlung("2025-02-01"), zahlung("2025-07-01"), zahlung("2025-08-01")]


class LueckenTest(Korrelation):
    def test_undokumentierte_luecken_ergeben_exit_1(self):
        ergebnis = self.korreliere(KONTO_MIT_LUECKE, abrechnung(DREI_ZAHLUNGEN))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("unverifizierbar: Zahlung 2025-02-01 250,00", ergebnis.stdout)
        self.assertIn("fehlt: Zahlung 2025-08-01 250,00", ergebnis.stdout)

    def test_dokumentierte_luecken_ergeben_exit_0(self):
        ergebnis = self.korreliere(KONTO_MIT_LUECKE, abrechnung(
            DREI_ZAHLUNGEN,
            "unverifizierbar: Zahlung 2025-02-01 250,00 – Auszug fehlt",
            "fehlt: Zahlung 2025-08-01 250,00 – Sammel-Lastschrift, in der Buchungsliste belegt"))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def test_eine_offene_luecke_genuegt_fuer_exit_1(self):
        ergebnis = self.korreliere(KONTO_MIT_LUECKE, abrechnung(
            DREI_ZAHLUNGEN, "unverifizierbar: Zahlung 2025-02-01 250,00 – Auszug fehlt"))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)

    def test_zahlung_eines_namensvetters_belegt_nichts(self):
        konto_json = konto(1000.00, 1250.00, auszug("1/2025", 1000.00, 1250.00, "2025-01-01", "2025-12-31",
                                                    buchung("2025-08-01", "Erika Müller", 250.00)))
        ergebnis = self.korreliere(konto_json, abrechnung([zahlung("2025-08-01")]))
        self.assertIn("fehlt: Zahlung 2025-08-01 250,00", ergebnis.stdout)

    def test_ohne_bankbuchung_des_eigentuemers_ist_das_eine_eigene_luecke(self):
        konto_json = konto(1000.00, 1000.00, auszug("1/2025", 1000.00, 1000.00, "2025-01-01", "2025-12-31"))
        ergebnis = self.korreliere(konto_json, abrechnung(
            [zahlung("2025-08-01")], "fehlt: Zahlung 2025-08-01 250,00 – Sammel-Lastschrift"))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("fehlt: Bankbuchung von Müller, Hans", ergebnis.stdout)


class FehltInAbrechnungTest(Korrelation):
    """Ein Eingang des Eigentümers in der Bank, den keine Zahlung erklärt, ist eine Lücke der Abrechnung."""

    def konto(self, *buchungen):
        return konto(1000.00, 1000.00, auszug("1/2025", 1000.00, 1000.00, "2025-01-01", "2026-01-31", *buchungen))

    def test_unerklaerter_eingang_ist_eine_luecke(self):
        ergebnis = self.korreliere(self.konto(buchung("2025-09-01", "Hans Müller", 250.00)), abrechnung([]))
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("fehlt in Abrechnung: Zahlung 2025-09-01 250,00", ergebnis.stdout)

    def test_eingang_ausserhalb_des_zeitraums_ist_keine_luecke(self):
        ergebnis = self.korreliere(self.konto(buchung("2026-01-05", "Hans Müller", 250.00)), abrechnung([]))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def test_zahlung_einer_anderen_einheit_desselben_eigentuemers_ist_keine_luecke(self):
        andere = abrechnung([zahlung("2025-09-01")], eigentuemer="Hans Müller", einheit=4)
        fremde = abrechnung([zahlung("2025-10-01")], eigentuemer="Erika Müller", einheit=5)
        ergebnis = self.korreliere(
            self.konto(buchung("2025-09-01", "Hans Müller", 250.00), buchung("2025-10-01", "Hans Müller", 250.00)),
            abrechnung([]), we4=andere, we5=fremde)
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertNotIn("2025-09-01", ergebnis.stdout)
        self.assertIn("fehlt in Abrechnung: Zahlung 2025-10-01 250,00", ergebnis.stdout)

    def test_zahlungseingang_auf_die_vorjahre_ist_keine_luecke(self):
        ergebnis = self.korreliere(self.konto(buchung("2025-04-15", "Hans Müller", 80.00)),
                                   abrechnung([], vorjahre=80.00))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
