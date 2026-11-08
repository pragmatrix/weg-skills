"""Tests für `etg24-portal/etg24_abgleich.py`.

Das Skript vergleicht Exporte der Dokumentenlisten des Portals mit der Abgleichliste über Bereich, Kategorie, Titel
und Datum. Ein falsch berechnetes Jahr oder eine übersprungene Zeile der Liste ändert diesen Schlüssel, und ein
bekanntes Dokument erscheint dann still als neu. Die Tests halten die Jahresregel für Daten ohne Jahr fest und die
Erkennung der Trennzeile. Alle Daten sind erfunden.
"""
import os
import unittest
from datetime import datetime

from _support import Projekt

SKRIPT = "etg24-portal/etg24_abgleich.py"
KOPF = "| Kategorie | Titel im Portal | Datum | Größe | Ablage | Portal |\n|---|---|---|---|---|---|\n"


class AbgleichTest(unittest.TestCase):
    def setUp(self):
        self.projekt = Projekt()
        self.addCleanup(self.projekt.close)

    def abgleich(self, datum, exporttag, zeilen=""):
        """Exportiert ein Dokument mit dem Datum `datum` am Tag `exporttag` (TT.MM.JJJJ) und ruft das Skript auf."""
        self.projekt.write("Verwaltung/Muster/ETG24-Abgleich.md", "# Abgleich\n\n## Objekt\n\n" + KOPF + zeilen)
        export = self.projekt.write("tmp/objekt.json", [
            {"category": "", "title": "Protokoll", "date": datum, "size": "12 kB", "type": "pdf"},
        ])
        zeit = datetime.strptime(exporttag + " 12:00", "%d.%m.%Y %H:%M").timestamp()
        os.utime(export, (zeit, zeit))
        return self.projekt.run(SKRIPT, export)

    def test_datum_nach_dem_exporttag_gehoert_ins_vorjahr(self):
        ergebnis = self.abgleich("18. Dezember", "05.01.2026")
        self.assertIn("| Protokoll | 18.12.2025 |", ergebnis.stdout)

    def test_datum_am_exporttag_bleibt_im_jahr(self):
        ergebnis = self.abgleich("5. Januar", "05.01.2026")
        self.assertIn("| Protokoll | 05.01.2026 |", ergebnis.stdout)

    def test_29_februar_faellt_ins_letzte_schaltjahr(self):
        ergebnis = self.abgleich("29. Februar", "01.03.2025")
        self.assertIn("| Protokoll | 29.02.2024 |", ergebnis.stdout)

    def test_unbekanntes_format_bricht_ab(self):
        ergebnis = self.abgleich("Dez. 18", "05.01.2026")
        self.assertNotEqual(ergebnis.returncode, 0)
        self.assertIn("Unbekanntes Datumsformat", ergebnis.stderr)

    def test_zeile_ohne_kategorie_ist_bekannt(self):
        ergebnis = self.abgleich("01.02.2025", "05.01.2026", "|  | Protokoll | 01.02.2025 | 12 kB | – |  |\n")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stderr)
        self.assertIn("## Objekt: 0 neu", ergebnis.stdout)


if __name__ == "__main__":
    unittest.main()
