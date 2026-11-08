# Checkliste Umsetzung von Beschlüssen

Gegenstand sind die Beschlüsse einer oder mehrerer Versammlungen. Geprüft wird, ob die Verwaltung sie ausgeführt hat
(§ 27 Abs. 1 WEG). Die Beschluss-Sammlung (§ 24 Abs. 7 WEG) ist das Verzeichnis, das Protokoll liefert Wortlaut,
Anmerkungen und Abstimmung.

**Quellen:** Beschluss-Sammlung, Beschlussprotokolle, danach erstellte Abrechnungen und Wirtschaftspläne,
Schriftverkehr in `Verwaltung/`, Vorgänge in `Vorgänge/` (Übersicht `Vorgänge/Vorgänge.md`).

## Prüfpunkte

1. **Verzeichnis vollständig:** Jeder Beschluss aus dem Protokoll steht in der Beschluss-Sammlung, mit gleichem
   Wortlaut und Ergebnis. Informationspunkte ohne Abstimmung zählen nicht, aber Zusagen darin (z. B. „Firma X soll
   gebeten werden“) nimmst du als Auftrag mit auf.
2. **Umsetzbare Beschlüsse auswählen:** Jeder zustande gekommene Beschluss verlangt etwas, z. B. Geld (Rücklage,
   Sonderumlage, Hausgeld), einen Auftrag, einen Vertrag, eine Frist oder eine Änderung von Schlüsseln. Für jeden
   Beschluss notierst du, woran die Umsetzung sichtbar würde und ab wann.
3. **Nachweis suchen:** Für jeden Beschluss aus Punkt 2 suchst du die Stelle, an der die Umsetzung sichtbar sein
   müsste, mit `grep -r --include='*.md'`. Beispiele: Rücklagenhöhe im Wirtschaftsplan, Verwaltervertrag im Ordner der
   Verwaltung, Auftrag oder Rechnung in der Abrechnung.
4. **Status je Beschluss:** Jeder Beschluss bekommt einen der vier Status aus Schritt 3 von `SKILL.md`.
   - **stimmt** heißt umgesetzt. Der Beleg zeigt die Umsetzung.
   - **Abweichung** heißt nicht umgesetzt. Der Beleg zeigt das Gegenteil.
   - **Frage** heißt, die Umsetzung ist unklar und die Verwaltung muss sie erklären.
   - **nicht prüfbar** nennt den Grund. Das ist entweder das fehlende Dokument oder „fällig ab <Datum>“ für einen
     Beschluss, der noch nicht fällig ist.
5. **Folgen beziffern:** Bei einem nicht umgesetzten Beschluss mit Geldwirkung rechnest du die Differenz aus, für
   die Gemeinschaft und die Einheiten des Nutzers.
6. **Fristen:** Anfechtungsfrist eines fehlerhaften Beschlusses (§ 45 WEG: Klage binnen eines Monats, Begründung
   binnen zwei Monaten nach Beschlussfassung) und Fälligkeiten, die aus Beschlüssen folgen, mit Datum nennen.

Der Bericht enthält eine Tabelle mit allen Beschlüssen: Nr., Kurzinhalt, TOP, erwartete Umsetzung, Status, Beleg.
„Nr.“ ist die Nummer des Prüfpunkts im Bericht (Abschnitt „Prüfpunkte im Bericht“ in `SKILL.md`). Die Nummer eines
Beschlusses in der Beschluss-Sammlung steht, wenn nötig, in einer eigenen Spalte hinter „TOP“.
