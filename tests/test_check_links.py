"""Tests für die Nummernprüfung in `weg-eigentuemer-ablage/scripts/check_links.py`.

Ein Link auf eine eigene MD, dessen Linktext oder Tooltip einen Punkt wie „Nr. 4.2“ nennt, braucht im Ziel einen Punkt
mit dieser Nummer. Links mit demselben Tooltip teilen sich ihre Ziele. Die Tests halten diese Regel fest und die
Fälle, in denen eine Nummer im Ziel nicht genügt: im Fließtext oder als Anfang einer längeren Nummer.
"""
import unittest

from _support import Projekt

SKRIPT = "weg-eigentuemer-ablage/scripts/check_links.py"


class NummernTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)
        self.projekt.write("Abrechnungen/mit.md", "# Prüfung\n\n- 4.2 Rücklage zu niedrig\n")
        self.projekt.write("Abrechnungen/ohne.md", "# Notiz\n\n- 4.21 Ein anderer Punkt\n")

    def pruefe(self, text):
        self.projekt.write("Abrechnungen/README.md", text)
        return self.projekt.run(SKRIPT)

    def test_gemeinsamer_tooltip_genuegt_in_einem_ziel(self):
        ergebnis = self.pruefe('[Bericht](<mit.md> "Nr. 4.2") und [Notiz](<ohne.md> "Nr. 4.2")\n')
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def test_link_ohne_tooltip_wird_fuer_sich_geprueft(self):
        ergebnis = self.pruefe("[Bericht Nr. 4.2](<mit.md>) und [Notiz Nr. 4.2](<ohne.md>)\n")
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("ohne.md", ergebnis.stdout)
        self.assertNotIn("mit.md", ergebnis.stdout)

    def test_laengere_nummer_im_ziel_zaehlt_nicht(self):
        ergebnis = self.pruefe('[Notiz](<ohne.md> "Nr. 4.2")\n')
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("Punkt 4.2 gibt es in ohne.md nicht", ergebnis.stdout)

    def test_nummer_im_fliesstext_des_ziels_zaehlt_nicht(self):
        self.projekt.write("Abrechnungen/prosa.md", "# Notiz\n\nSiehe Abschnitt 4.2. Danach folgt der Rest.\n")
        ergebnis = self.pruefe('[Notiz](<prosa.md> "Nr. 4.2")\n')
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("Punkt 4.2 gibt es in prosa.md nicht", ergebnis.stdout)

    def test_laengere_vertragsnummer_im_ziel_zaehlt_nicht(self):
        self.projekt.write("Abrechnungen/vertrag.md", "# Vertrag\n\nLaut Nr. 4.2.1 trägt die Verwaltung die Kosten.\n")
        ergebnis = self.pruefe('[Vertrag](<vertrag.md> "Nr. 4.2")\n')
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("Punkt 4.2 gibt es in vertrag.md nicht", ergebnis.stdout)

    def test_link_ohne_spitze_klammern_wird_geprueft(self):
        ergebnis = self.pruefe('[Notiz](ohne.md "Nr. 4.2")\n')
        self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout)
        self.assertIn("Punkt 4.2 gibt es in ohne.md nicht", ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
