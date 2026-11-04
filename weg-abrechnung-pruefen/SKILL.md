---
name: weg-abrechnung-pruefen
description: Prüfbericht zu WEG-Unterlagen erstellen. Für die Jahresabrechnung (Gesamtabrechnung oder Einzelabrechnung einer Einheit), den Wirtschaftsplan, die Umsetzung von Beschlüssen der Eigentümerversammlung oder eine neue Fassung eines Vertrags wie des Verwaltervertrags.
---

# WEG-Unterlagen prüfen

Der Nutzer ist Eigentümer oder Bevollmächtigter und prüft, was die Verwaltung vorlegt. Jede Prüfung endet in einem
**Prüfbericht**. Das ist eine Markdown-Datei, in der jeder Prüfpunkt einen Status und einen Beleg hat.

Es gibt fünf Prüfungen. Jede hat eine eigene Checkliste in diesem Ordner.

| Prüfung | Checkliste | Gegenstand |
|---|---|---|
| Gesamtabrechnung | [gesamt.md](gesamt.md) | Geldkonten, Ausgaben, Rücklage und Vermögen der ganzen Gemeinschaft |
| Einzelabrechnung | [einheit.md](einheit.md) | Anteile, Summen und Nachschuss einer Einheit |
| Wirtschaftsplan | [wirtschaftsplan.md](wirtschaftsplan.md) | Ansätze, Schlüssel und Vorschüsse für das Planjahr |
| Beschlüsse | [beschluesse.md](beschluesse.md) | ob jeder Beschluss in Abrechnung, Plan oder Handeln der Verwaltung umgesetzt ist |
| Vertrag | [vertrag.md](vertrag.md) | jede Änderung der neuen gegenüber der bisherigen Fassung, mit Kosten und Gewichtung |

## Schritte

1. **Umfang klären.** Bestimme, welche Prüfungen, welches Jahr und welche Einheiten verlangt sind. Ist das unklar,
   frage den Nutzer. Lies nur die Checklisten der gewählten Prüfungen. Bei einer Jahresabrechnung kommt die
   Gesamtabrechnung vor den Einzelabrechnungen, weil diese auf den Gesamtbeträgen aufbauen. Fertig ist der Schritt,
   wenn Prüfungen, Jahr und Einheiten feststehen.
2. **Quellen sammeln.** Lies zuerst die Eigenheiten der Unterlagen (Abschnitt unten), dann die Text-MD neben jedem
   PDF (`X.pdf` → `X.md`). Die Checkliste nennt, welche Dokumente nötig sind. Fehlt ein Dokument, ist das selbst ein
   Befund. Bestehende Prüfberichte (`Pruefung_*.md`) zum selben Jahr nimm als Ausgangspunkt, statt noch einmal von
   vorn anzufangen. Fertig ist der Schritt, wenn jedes Dokument, das die Checkliste nennt, gelesen oder als fehlend
   notiert ist.
3. **Jeden Prüfpunkt abarbeiten.** Jeder Punkt der Checkliste bekommt einen von vier Status:
   - **stimmt**: nachgerechnet oder abgeglichen, kein Unterschied
   - **Abweichung**: Unterschied mit Betrag und Fundstellen auf beiden Seiten
   - **Frage**: plausibel unklar, Erklärung der Verwaltung nötig
   - **nicht prüfbar**: mit Grund, z. B. welches Dokument fehlt

   Summen, Anteile und Differenzen rechnest du mit einem kurzen Python-Skript nach, nicht im Kopf. Fertig ist der
   Schritt, wenn jeder Prüfpunkt einen Status hat.
4. **Am PDF belegen.** Jede Zahl, die in den Bericht geht, prüfst du am PDF nach. Wo Spalten in der MD
   verrutscht wirken, siehst du dir das Seitenbild an (`pdftoppm -r 80 -f N -l N`, Ausgabe nach `tmp/`). Fertig ist
   der Schritt, wenn jede Zahl für den Bericht mit PDF-Seite und Position notiert ist.
5. **Bericht schreiben** nach dem Aufbau unten. Fertig ist der Schritt, wenn der Bericht jeden Teil der Gliederung
   enthält und als Dokument nach dem Abschnitt „Quellenlinks“ im Skill `weg-eigentuemer-ablage` fertig ist.
6. **Nachziehen.** Trage den Bericht mit einer Zeile in die `README.md` seines Hauptordners ein (Pfad, Ergebnis,
   wichtigste Zahl). Nenne dem Nutzer das Fazit, Fristen mit Datum und den nächsten sinnvollen Schritt. Das ist meist
   ein Entwurf an die Verwaltung. Fertig ist der Schritt, wenn die Zeile in der `README.md` steht und der Nutzer Fazit,
   Fristen und nächsten Schritt kennt.

## Belege

- Jeder Beleg ist ein Quellenlink nach dem Abschnitt „Quellenlinks“ im Skill `weg-eigentuemer-ablage`. Dort steht
  auch, welche Seite zählt. Linktext Beispiel: „Abr. 2023 E4, S. 3“.
- Der Tooltip nennt Dokument mit Erstellungsdatum, PDF-Seite und Position. Beispiel: „Jahresabrechnung 2023 Einheit 4,
  erstellt am 12.04.2024, S. 3, Erhaltung Heizung“.
- Abrechnungen können neu gefasst werden. Deshalb nennt der Tooltip immer das Erstellungsdatum. Wo es in den
  Unterlagen der Verwaltung steht, etwa im Dateinamen oder auf dem Deckblatt, hält der Abschnitt „Eigenheiten der
  Unterlagen“ der `Abrechnungen/README.md` fest.
- Zitate aus Beschlüssen wörtlich, mit TOP-Nummer und Seite des Protokolls bzw. Nummer in der Beschluss-Sammlung.

## Aufbau des Prüfberichts

Ablage beim Thema, Name ohne Datum am Anfang (keine Kollision mit Dateien der Verwaltung):

- Jahresabrechnung: `Abrechnungen/JJJJ/Pruefung_Abrechnung_JJJJ_<Gesamt|Einheit_N>[_Vergleich_VORJAHR].md`
- Wirtschaftsplan: `Abrechnungen/JJJJ/Pruefung_Wirtschaftsplan_PLANJAHR[_Thema].md`, im Ordner des Jahres, mit
  dessen Abrechnung der Plan kam
- Beschlüsse: `Versammlungen/Pruefung_Beschluesse_<Versammlungsdatum JJJJMMTT>.md`
- Vertrag: neben dem Vertrag, z. B. `Verwaltung/<Verwaltung>/Pruefung_Verwaltervertrag_<Beginn>_Vergleich_<alte Fassung>.md`

Gliederung:

1. Kopf: Gegenstand, Objekt, Einheiten mit MEA, Prüfstand (heutiges Datum)
2. **Kurzfazit**: stimmig ja oder nein, Ergebnis für die Einheit (Nachschuss, neuer Vorschuss), die größten
   Abweichungen mit Betrag
3. Ein nummerierter Abschnitt je Prüfung, darin eine Tabelle der Prüfpunkte nach dem Abschnitt „Prüfpunkte im
   Bericht“. Die Prüfpunkte tragen die Abschnittsnummer davor (1.1, 1.2, 2.1).
4. **Fragen an die Verwaltung** als nummerierter Abschnitt, die Fragen mit dessen Nummer davor (4.1, 4.2) und so
   formuliert, dass man sie ins Schreiben übernehmen kann
5. **Empfehlung** zum anstehenden Beschluss: zustimmen, ablehnen oder vorher Nachbesserung verlangen. Bei
   bleibenden Zweifeln Belegeinsicht vorschlagen (§ 18 Abs. 4 WEG).
6. **Quellen**: alle benutzten Dateien als Links, mit Seiten

Namen und Rückstände anderer Eigentümer gehören nicht in den Bericht. Fasse sie als Summe zusammen.

Listen, Nummern, Gewichtung und Veränderungen als Betrag und Prozentsatz folgen dem Abschnitt „Gliederung und
Gewichtung“ im Skill `weg-eigentuemer-ablage`.

### Prüfpunkte im Bericht

Dieses Format liest auch der Skill `pdf-annotate`, wenn er die Prüfpunkte in einer Kopie des PDFs markiert.

- Ein Prüfpunkt ist eine Zeile einer Tabelle. Die erste Zeile der Tabelle nennt die Spalten. Die Spalte „Nr.“ trägt
  die Nummer des Prüfpunkts, die Spalte „Status“ einen der vier Status aus Schritt 3 und die Spalte „Beleg“ den
  Quellenlink. Weitere Spalten wie „Prüfpunkt“, „Befund“ oder „Betrag“ sind frei. Die erste davon nennt den
  Prüfpunkt.
- Eine Zelle darf leer bleiben. Ein senkrechter Strich in einer Zelle steht als `\|`.
- Fragen, Änderungswünsche und andere nummerierte Punkte außerhalb einer Tabelle sind Listenpunkte mit der Nummer
  vorn (`- 4.1 Text`) oder Checklistenpunkte (`- [ ] 4.1 Text`). Eingerückte Folgezeilen gehören zum Punkt.
- Die Nummer hat die Form aus dem Abschnitt „Gliederung und Gewichtung“ im Skill `weg-eigentuemer-ablage`, also
  etwa 1.2, 1.2.3 oder 1.4b.
- Teilt ein Abschnitt seine Punkte nach Gewicht, heißen die Unterabschnitte `### Wichtig` und
  `### Akzeptabel oder nachrangig`.

## Eigenheiten der Unterlagen

Jede Verwaltung und jeder Messdienst baut seine Unterlagen anders auf. Was davon für das Objekt gilt, steht im
Abschnitt „Eigenheiten der Unterlagen“ der `Abrechnungen/README.md`. Dazu gehören:

- der Seitenaufbau von Jahresabrechnung, Wirtschaftsplan und Heizkostenabrechnung
- wo das Erstellungsdatum einer Abrechnung steht
- Störungen in der Text-MD, etwa unsichtbare Kontonummern
- der Suchbegriff für die Seiten einer Einheit in der Heizkostenabrechnung
- Einheiten ohne Heizkosten oder Vorschuss
- Jahre ohne Vergleichszahlen

Findest du eine neue Eigenheit, trägst du sie dort ein.

## Werkzeuge

Die Rezepte dieses Skills liegen in `pruefen.just` neben dieser Datei. Die `justfile` des Projekts bindet sie ein
mit `import '.claude/skills/weg-abrechnung-pruefen/pruefen.just'`, dazu die Rezepte des Skills
`weg-eigentuemer-ablage`. Fehlt der Import, trägst du ihn ein. Ein neues Projekt richtet
der Skill `weg-eigentuemer-ablage` ein (Abschnitt Neues Projekt einrichten).
