"""Tests für die Suche einer Stelle in `pdf-annotate/pdf_annotate.py`, mit Wortlisten statt eines PDFs.

Ein Wort ist ein Tupel wie aus PyMuPDF: (x0, y0, x1, y1, Text, Block, Zeile, Wortnummer), mit den Koordinaten in
Punkten. Das Modul braucht PyMuPDF beim Import. Ohne das Paket werden die Tests übersprungen. Mit dem Paket laufen sie
so:
    uv run --with pymupdf python -m unittest discover -s tests
"""
import importlib.util
import types
import unittest

from _support import module

HAT_PYMUPDF = importlib.util.find_spec("pymupdf") is not None
SEITE = types.SimpleNamespace(number=0)


def zeile(y, *texte, x=50):
    """Wörter auf einer Zeile mit der Oberkante `y`, je 40 Punkte breit und 10 Punkte hoch."""
    return [(x + 50 * i, y, x + 50 * i + 40, y + 10, t, 0, 0, i) for i, t in enumerate(texte)]


@unittest.skipUnless(HAT_PYMUPDF, "PyMuPDF fehlt")
class StellenTest(unittest.TestCase):
    def setUp(self):
        self.pa = module("pdf-annotate", "pdf_annotate")

    def test_erster_teil_endet_sein_wort_letzter_beginnt_seins(self):
        woerter = zeile(100, "Verwaltung", "der", "Gemeinschaft")
        self.assertTrue(self.pa.fits(woerter, 0, ["waltung", "der", "Gemein"]))
        self.assertFalse(self.pa.fits(woerter, 0, ["Verwal", "der", "Gemeinschaft"]))
        self.assertFalse(self.pa.fits(woerter, 0, ["Verwaltung", "der", "schaft"]))

    def test_mittlere_teile_muessen_ganz_passen(self):
        woerter = zeile(100, "Verwaltung", "der", "Gemeinschaft")
        self.assertFalse(self.pa.fits(woerter, 0, ["Verwaltung", "de", "Gemeinschaft"]))

    def test_einzelner_teil_darf_mitten_im_wort_stehen(self):
        self.assertTrue(self.pa.fits(zeile(100, "Verwaltungsbeirat"), 0, ["tungsbei"]))

    def test_alle_woerter_auf_einer_zeile(self):
        # Eine Unterkante 2 Punkte tiefer zählt noch zur Zeile, 3 Punkte tiefer nicht mehr.
        nah = zeile(100, "Verwaltung") + zeile(102, "der", x=100)
        fern = zeile(100, "Verwaltung") + zeile(103, "der", x=100)
        self.assertTrue(self.pa.fits(nah, 0, ["Verwaltung", "der"]))
        self.assertFalse(self.pa.fits(fern, 0, ["Verwaltung", "der"]))

    def test_lesereihenfolge_innerhalb_einer_zeile_von_links_nach_rechts(self):
        # Die Tabelle ist Spalte für Spalte gespeichert. Die rechte Zelle steht 3 Punkte tiefer, aber auf derselben Zeile.
        rechts = zeile(103, "gesondert", x=300)
        links = zeile(100, "Hausmeister")
        darunter = zeile(104, "Reinigung")
        texte = [w[4] for w in self.pa.reading_order(rechts + darunter + links)]
        self.assertEqual(texte, ["Hausmeister", "gesondert", "Reinigung"])

    def test_match_waehlt_das_vorkommen(self):
        woerter = zeile(100, "Rücklage", "laut", "Plan") + zeile(120, "Rücklage", "laut", "Abrechnung")
        self.assertEqual(self.pa.locate(SEITE, woerter, "Rücklage laut", 2), (3, 4))

    def test_mehrfacher_treffer_ohne_match_bricht_ab(self):
        woerter = zeile(100, "Rücklage", "laut", "Plan") + zeile(120, "Rücklage", "laut", "Abrechnung")
        with self.assertRaises(SystemExit):
            self.pa.locate(SEITE, woerter, "Rücklage laut", None)
        with self.assertRaises(SystemExit):
            self.pa.locate(SEITE, woerter, "Rücklage laut", 3)


if __name__ == "__main__":
    unittest.main()
