"""Tests für `wert` in `weg-vermieter-nebenkosten/verify_abrechnung_xlsx.py`, die Auswertung der Formeln einer
Abrechnung.

`wert` rechnet Formeln aus Zellbezügen, Zahlen, +, −, Klammern und SUM selbst aus, weil openpyxl keine berechneten
Werte schreibt. Jede andere Formel muss abbrechen, damit sie nicht ungeprüft durchgeht. Ohne openpyxl werden die
Tests übersprungen.
"""
import importlib.util
from decimal import Decimal
import unittest

from _support import module

HAT_OPENPYXL = importlib.util.find_spec("openpyxl") is not None


@unittest.skipUnless(HAT_OPENPYXL, "openpyxl fehlt")
class WertTest(unittest.TestCase):
    def setUp(self):
        from openpyxl import Workbook
        self.verify = module("weg-vermieter-nebenkosten", "verify_abrechnung_xlsx")
        self.ws = Workbook().active
        self.ws["F1"], self.ws["F2"] = 10, 4

    def wert(self, formel):
        self.ws["A1"] = formel
        return self.verify.wert(self.ws, 1, 1)

    def test_vorzeichen_und_verschachtelte_klammern(self):
        self.assertEqual(self.wert("=-(F1-(F2+1))"), Decimal(-5))
        self.assertEqual(self.wert("=-F1+F2"), Decimal(-6))
        self.assertEqual(self.wert("=SUM(F1:F2)-(-F2)"), Decimal(18))

    def test_bereich_ausserhalb_von_sum(self):
        with self.assertRaises(ValueError):
            self.wert("=F1:F2")

    def test_unbekannte_funktion(self):
        with self.assertRaises(ValueError):
            self.wert("=ROUND(F1,0)")

    def test_zyklischer_bezug(self):
        self.ws["B1"] = "=A1"
        with self.assertRaises(ValueError):
            self.wert("=B1")


if __name__ == "__main__":
    unittest.main()
