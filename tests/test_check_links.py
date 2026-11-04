"""Tests für die Nummernprüfung in `weg-eigentuemer-ablage/scripts/check_links.py`.

Ein Link auf eine eigene MD, dessen Linktext oder Tooltip einen Punkt wie „Nr. 4.2“ nennt, braucht im Ziel einen Punkt
mit dieser Nummer. Links mit demselben Tooltip teilen sich ihre Ziele. Die Tests halten diese Regel und die Formen
fest, in denen ein Punkt im Ziel beginnen darf.
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

    def test_formen_eines_punkts_im_ziel(self):
        ziele = {
            "liste": "- 4.2 Text",
            "checkliste": "- [ ] 6.1 Text",
            "tabelle": "| Nr. | Prüfpunkt |\n|---|---|\n| 1.8c | Text |",
            "ueberschrift": "## 3. Ergebnis",
            "nummeriert": "5. Text",
        }
        for name, text in ziele.items():
            self.projekt.write(f"Abrechnungen/{name}.md", text + "\n")
        links = [('liste', "Nr. 4.2"), ('checkliste', "Frage 6.1"), ('tabelle', "Prüfpunkt 1.8c"),
                 ('ueberschrift', "Ergebnis 3"), ('nummeriert', "Nr. 5")]
        ergebnis = self.pruefe("".join(f'[{name}](<{name}.md> "{punkt}")\n' for name, punkt in links))
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
