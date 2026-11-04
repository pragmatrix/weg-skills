# Checkliste Vertrag

Gegenstand ist die neue Fassung eines Vertrags der Gemeinschaft, meist des Verwaltervertrags, im Vergleich mit der
bisherigen Fassung. Die Prüfung soll vor dem Beschluss über den Vertrag fertig sein.

**Quellen:** beide Fassungen als PDF, die letzte Jahresabrechnung und der Wirtschaftsplan für die bisherigen Kosten,
Beschlüsse zum Vertrag und zu Ermächtigungen des Vertragspartners.

## Prüfpunkte

1. **Vollständiger Vergleich:** `just vergleich ALT.pdf NEU.pdf > tmp/vergleich.txt` listet jede geänderte Stelle.
   Jede Stelle bekommt im Bericht einen Eintrag mit Fundstelle in beiden Fassungen und der Bewertung besser,
   schlechter oder neutral. Rein redaktionelle Änderungen fasst eine Zeile zusammen. Fertig ist der Punkt, wenn jede
   `===`-Stelle der Ausgabe einem Eintrag zugeordnet ist.
2. **Pauschalen und Gebühren:** Für jede Pauschale stehen alt und neu nebeneinander: Betrag, Bezugsgröße (Gemeinschaft,
   Einheit, Grundbucheinheit, Fall), Zeitraum und Bedingung. Fehlt eine dieser Angaben im Vertrag, ist das ein Befund.
3. **Grund- und besondere Leistungen:** Jede Tätigkeit, die die Spalte wechselt oder eine neue Stunden- oder
   Betragsgrenze bekommt, ist ein eigener Eintrag. Die Wirkung rechnest du an einem Fall aus dem Haus nach, etwa an
   einem vergangenen Schaden oder einer Maßnahme.
4. **Kosten für die Gemeinschaft:** Eine Tabelle mit bisherigem Betrag, neuem Betrag und Mehrkosten je Posten. Die
   bisherigen Beträge kommen aus Abrechnung und Wirtschaftsplan.
5. **Preisanpassung ohne Beschluss:** Indexklauseln, Weitergabe von Kosten Dritter und Beträge mit „z. Zt.“.
6. **Widersprüche und Fehler:** im neuen Text und in der alten Fassung. Ein Widerspruch der alten Fassung schwächt
   Argumente, die sich auf sie stützen.
7. **Gewichtung:** Ergebnis und Änderungswünsche sind in „wichtig“ und „akzeptabel oder nachrangig“ geteilt,
   Verbesserungen stehen getrennt. Die Änderungswünsche stehen in einem nummerierten Abschnitt und sind über beide
   Gruppen fortlaufend nummeriert (etwa 5.1 bis 5.12), damit andere Unterlagen sie zitieren können.

Wünscht der Nutzer den neuen Vertrag mit markierten Prüfpunkten und Änderungen, erzeuge ihn danach mit dem Skill
`pdf-annotate`.
