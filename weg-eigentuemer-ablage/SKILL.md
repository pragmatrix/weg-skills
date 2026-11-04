---
name: weg-eigentuemer-ablage
description: Ordnerstruktur, Ablage und Verwaltungsprozesse einer Eigentumswohnung (WEG) aus Eigentümersicht: Projekt einrichten, Dokumente ablegen, Vorgänge anlegen und archivieren, Versammlung vorbereiten, Anträge stellen.
---

# WEG-Unterlagen aus Eigentümersicht

Gilt für Projektordner zu einer Eigentumswohnung in einer Wohnungseigentümergemeinschaft (WEG). Sprache: Deutsch.
Der Nutzer ist Eigentümer oder bevollmächtigter Vertreter, nicht Verwalter.

Zuerst immer die `AGENTS.md` im Wurzelordner lesen: Sie nennt Einheiten mit ihren Kennungen, Beteiligte, Verwaltung,
offene Themen und die Grundregeln für Agenten (Fragen vor dem Verschieben, Originale, Entwürfe, personenbezogene
Daten). Was dort steht, geht diesem Skill vor.

## Grundregeln

- Jedes neue Dokument belegt seine Fakten mit Quellenlinks (siehe Abschnitt Quellenlinks).
- Nach jedem neuen oder geänderten Dokument die `README.md` seines Hauptordners nachziehen.
- Kommt eine Übersicht hinzu, entfällt eine oder ändert sich ihr Pfad, die `README.md` im Wurzelordner nachziehen.
  Dort auch jede neue Einladung, jedes Protokoll und jede Beschluss-Sammlung unter ihrem Jahr eintragen.

## Werkzeuge

Die Skripte dieses Skills liegen in `scripts/` neben dieser Datei. Sie arbeiten im **Projektordner**, also im
Wurzelverzeichnis des Git-Repositorys, in dem der aktuelle Ordner liegt. Aufgerufen werden sie über `just`. Die
`justfile` des Projekts bindet die Rezepte ein:

```
import '~/.claude/skills/weg-eigentuemer-ablage/scripts/ablage.just'
```

Liegen die Skills woanders als in `~/.claude/skills`, nennt der Import diesen Ort. `just --list` zeigt die Rezepte
mit Beschreibung. Ein neues Projekt richtest du nach dem Abschnitt Neues Projekt einrichten ein. Fehlt in einem
bestehenden Projekt nur der Import, trägst du ihn ein. Die Skripte brauchen `python3`, Git und Poppler
(`pdftotext`, `pdfinfo`, `pdftoppm`), für Scans ohne Textebene auch Tesseract.

Projektdaten der Skripte stehen im Projekt: `scripts/pdf2md-ignore.txt` nennt PDFs ohne Text-MD,
`scripts/dupes-ignore.txt` gewollte Kopien.

## Ordnerstruktur

```
AGENTS.md          Projektbeschreibung, Einheiten, Beteiligte, Verweise auf die Übersicht je Ordner
justfile           bindet die Rezepte der Skills ein (siehe Werkzeuge)
README.md          Einstieg für den Nutzer: Links auf alle Übersichten (Vorgänge.md, README.md je Hauptordner,
                   Notizen/, AGENTS.md), dazu je Jahr die Versammlungen und Beschluss-Sammlungen, neuestes Jahr
                   zuerst, ohne Beträge
*/README.md        Übersicht je Hauptordner: jedes Dokument mit Pfad, Inhalt, wichtigster Zahl
Abrechnungen/      ein Ordner pro Abrechnungsjahr (JJJJ/): Jahresabrechnung, Wirtschaftsplan, Heizkosten,
                   Versorgerrechnungen, Vermögensbericht, eigene Prüfungen, charts/, Belege eigener Zahlungen
                   an die Gemeinschaft (im Jahr, zu dem die Zahlung gehört). Liegen Kontoauszüge und Belege der
                   Gemeinschaft vor: Konto/, Belege/ und die Datenbasis daraus (Skill weg-konten-belege)
Versammlungen/     Einladungen, Protokolle, Beschluss-Sammlung, eigene Anträge an die Versammlung
Verwaltung/        ein Unterordner je Verwaltung (Name/): Verträge, Schriftverkehr, Formulare, Übergaben,
                   Rechnungen der Verwaltung an die Gemeinschaft (Vergütung, Mehraufwand, Sonderleistungen)
Stammdaten/        Teilungserklärung (+ Nachträge), Datenblätter, Eigentümerliste, Vollmachten/
Vorgänge/          Vorgänge.md (einzige Übersicht), ein Ordner je größerem Vorgang (ART JJJJMM Kurzname/),
                   Archiv/ für abgeschlossene Vorgänge (siehe Abschnitt Vorgänge)
Vermietung/        nur bei vermieteter Einheit: Mietvertrag/, ein Ordner je Abrechnungsjahr (JJJJ/) mit der
                   Nebenkostenabrechnung für den Mieter (Skill weg-vermieter-nebenkosten), Schriftverkehr mit dem Mieter
scripts/           eigene Skripte, die Ausarbeitungen erzeugen (Pfade relativ zum Projektordner), die
                   Ausnahmelisten pdf2md-ignore.txt und dupes-ignore.txt, hooks/ mit dem pre-commit-Hook
tmp/               Zwischenstände (Seitenbilder, Renderings); per .gitignore ausgeschlossen, darf weg
```

Wirtschaftspläne liegen im Ordner des Jahres, mit dessen Abrechnung sie verschickt wurden; im Namen steht das
Planjahr.

Bietet die Verwaltung eine Belegprüfung in ihrem Portal an (etwa ETG24), enthält sie Einzelbelege. Rechnungen der
Verwaltung selbst werden daraus abgelegt, weil sie die Verwaltervergütung der Abrechnung erklären. Belege von
Handwerkern und Versorgern bleiben im Portal.

## Namenskonvention

- Datierte Dateien und Ordner: `JJJJMMTT Beschreibung.ext`, Datum ohne Bindestriche, dann ein Leerzeichen.
  Beispiel: `20230522 Protokoll Versammlung.pdf`, `20230614 Bauamt Scans/`. Vorgangsordner heißen anders
  (`ART JJJJMM Kurzname/`, siehe Abschnitt Vorgänge).
- Maßgeblich ist das Datum des Dokuments (Briefdatum, Versammlungstag, Rechnungsdatum), nicht das des Scans oder
  Downloads. Ist nur der Monat bekannt, keinen Tag erfinden: Datum weglassen und den Stand in den Namen schreiben
  (`Verwaltervertrag Muster Stand März 2023.pdf`).
- Dateien, die die Verwaltung systematisch erzeugt (Einzelabrechnungen, Wirtschaftspläne, Exporte mit Objektnummer),
  behalten ihren Originalnamen; die Objektnummer-Präfixe in der `AGENTS.md` erklären.
- Beschreibung kurz und sprechend: Dokumentart, Absender oder Gegenstand. Keine Namen wie `scan 1.pdf`,
  `Vollmacht, X.pdf`. Mehrere Scans desselben Dokuments: `… - Scan 2.pdf`.
- Byte-gleiche Dubletten (`just dup`) dem Nutzer zum Löschen vorschlagen. Gewollte Kopien kommen in
  `scripts/dupes-ignore.txt`.
- Zu PDFs mit Textebene, auch Tabellen wie Abrechnungen, gehört eine generierte `X.md` mit dem Text (Markierung in
  Zeile 1, nie von Hand bearbeiten). Handschriftliche Scans, Pläne, erzeugte PDFs, Kopien und Formulare bekommen
  keine; Muster dafür in `scripts/pdf2md-ignore.txt` pflegen.
  Nach jedem Umbenennen oder Verschieben von PDFs `just md-prune` ausführen, damit keine verwaisten MDs bleiben.
  Eigene Ausarbeitungen nie so benennen wie ein PDF.

## Quellenlinks

Jedes neue Dokument, das du schreibst, belegt jeden Fakt mit einem kurzen Quellenlink. Über ihn öffnet der Nutzer das
Dokument mit einem Klick. Das gilt für Ausarbeitungen, Prüfberichte, Vorbereitungen der Versammlung, `NOTIZEN.md`
und Übersichten. Ein Fakt ist eine Zahl, ein Datum, ein Beschluss, ein Zitat oder eine Aussage über ein Dokument.
Markdown-Fußnoten (`[^x]`) zeigt der Previewer von VS Code nicht an, deshalb steht die Quelle als normaler Link direkt
im Text.

- Der Quellenlink steht in Klammern direkt hinter der Aussage, vor dem Satzzeichen. Mehrere Quellen trennt ein
  Semikolon. Beispiel:
  `beschlossen ([Protokoll 22.05.2023, S. 4](<../20230522 Beschlussprotokoll Versammlung.pdf> "Beschlussprotokoll vom 22.05.2023, S. 4, TOP 7")).`
- In einer Tabelle steht der Quellenlink in der Spalte „Beleg“ oder „Fundstelle“, sonst hinter dem Wert.
- Der Linktext ist kurz: Kurzname des Dokuments und Seite, bei der Tagesordnung der TOP, bei einem Prüfbericht der
  Abschnitt. Beispiele: „Abr. 2023 E4, S. 3“, „WP 2024 E4, S. 1“, „Heizkosten 2023, S. 7“, „Tagesordnung, TOP 9“,
  „Vertragsentwurf, S. 10“, „Prüfung Heizkosten, Abschnitt 1“. Der Pfad folgt der Regel unter „Verweise“ im Abschnitt
  Vorgänge.
- Der Tooltip (Titel in Anführungszeichen) nennt das Dokument ausgeschrieben, Seite und Position und jeden Hinweis,
  etwa dass eine Quelle eine Aussage nur zum Teil stützt.
- Die Seite zählt wie unter „Belege“ im Skill `weg-abrechnung-pruefen`. Der Link zeigt auf die Datei, die Seite steht im
  Linktext.
- Eine abgeleitete Zahl verlinkt den Abschnitt des Prüfberichts, der sie herleitet. Eine eigene Rechnung steht als
  Klammertext „(eigene Rechnung: …)“. Eine eigene Beobachtung verlinkt die Notiz in `Notizen/`.
- Gesetzesstellen und Aussagen, die schon auf ihre Quelle verlinken, kommen ohne Quellenlink aus.
- Texte für Dritte (Schreiben, Anträge, die versandt werden) nennen die Quelle als Text, z. B. „Abrechnung 2025,
  S. 3“, weil der Empfänger lokale Links nicht öffnen kann.
- Jede Seite wird an der Text-MD nachgeschlagen, mit `just seite MUSTER PDF…`. Stützt die Quelle eine Aussage nicht,
  wird das dem Nutzer gemeldet.
- Werden Quellenlinks in ein bestehendes Dokument nachgetragen, bleibt der Wortlaut gleich. `just wortdiff DATEI`
  meldet jedes Wort, das gegenüber Git weggefallen ist.

Fertig ist ein Dokument, wenn jeder Fakt einen Quellenlink hat und `just qa` keine Meldung mehr zeigt. Es meldet
fehlende Linkziele, Quellenlinks, deren Seite oder Zitat nicht zum PDF passt, und Verweise auf nummerierte Punkte
wie „Prüfpunkt 1.4b“, die es im Ziel nicht gibt. Dazu nennt es Beträge, Prozente und Daten ohne Quellenlink in neuen
und geänderten Blöcken (`just unbelegt`, alte Lücken mit `--alle`). Jede solche Meldung bekommt einen Quellenlink
oder wird dem Nutzer als unbelegt genannt.

## Gliederung und Gewichtung

Diese Regeln gelten für alles, was du für den Nutzer schreibst: Prüfberichte, Hochrechnungen, TOP-Dokumente,
`NOTIZEN.md`.

- Eine Aufzählung steht als Liste, ein Punkt je Aussage mit ihrem Quellenlink. Reiht ein Absatz mehrere Befunde,
  Beträge oder Argumente aneinander, teilst du ihn in Unterpunkte.
- Beginnt ein Listenpunkt mit einem Stichwort und Doppelpunkt, steht das Stichwort samt Doppelpunkt fett, etwa
  `- [ ] **Dach:** Laut …` oder `- **Kopierpauschale:** bis zu …`.
- Jeder Vergleich zweier Werte nennt die Veränderung als Betrag und als Prozentsatz. Das gilt für Mehrkosten,
  Erhöhungen und Abweichungen gegenüber Vorjahr, Plan, Hochrechnung oder alter Fassung. Der Prozentsatz bezieht sich
  auf den bisherigen Wert desselben Postens, etwa „Portalgebühr 30,00 € → 36,00 € (+20,0 %)“. Ein Posten ohne
  bisherigen Wert heißt „neu“. Eine Vergleichstabelle hat dafür eine Spalte „Veränderung“, auch im Kurzfazit steht
  der Prozentsatz. Die Prozentsätze rechnest du im selben Python-Skript wie die Beträge.
- **Sachlich:** Ein Dokument nennt Fakten, Fragen und Möglichkeiten mit ihren Folgen, etwa „Wer zustimmt, kann
  später schwerer anfechten“. Wie der Nutzer auftritt und was er fordert, entscheidet er selbst. Abschnitte wie
  „Haltung“ oder „Grundhaltung“, Hinweise zum Ton und wertende Wörter („still korrigiert“, „blind genehmigen“) gehören
  deshalb nicht hinein.
- Befunde, Argumente und Forderungen stehen nach **Gewicht**. Zuerst kommt „wichtig“, also was viel Geld kostet oder
  die Kontrolle über die Verwaltung schwächt. Danach folgt „akzeptabel oder nachrangig“. Verbesserungen stehen
  getrennt.
- Jede Nummer kommt in einem Dokument nur einmal vor, damit ein Verweis genau einen Punkt trifft. Eine Nummer
  bekommen die inhaltlichen Punkte: Befunde, Prüfpunkte, Gründe, Forderungen, Fragen, Änderungswünsche und
  Checklistenpunkte. Unterpunkte und Listen wie Unterlagen oder Quellen bleiben ohne Nummer.
  - Hat ein Dokument nur eine nummerierte Liste, zählt sie 1, 2, 3.
  - Hat es mehrere, bekommt jeder Abschnitt mit nummerierten Punkten eine Nummer (`## 4. Fragen an die Verwaltung`).
    Seine Punkte tragen die Abschnittsnummer davor: 4.1, 4.2. Ein Unterabschnitt verlängert die Nummer (1.2.3).
    Ein Zusatzpunkt bekommt einen Buchstaben (1.4a, 1.4b).
  - Ein Punkt mit Abschnittsnummer steht als Listenpunkt mit der Nummer vorn: `- 4.1 Text`. Ein Checklistenpunkt
    trägt die Nummer hinter dem Kästchen: `- [ ] 6.1 Text`. In einer Tabelle steht die Nummer in der Spalte „Nr.“.
  - Ein Verweis nennt Art und Nummer, etwa „Frage 4.2“ oder „Prüfpunkt 1.4a“. Liegt der Punkt in einem anderen
    Dokument, steht dessen Kurzname davor: „Prüfung Abr. 2025, Prüfpunkt 1.4a“.
  - Ändert sich eine Nummer, ziehst du jeden Verweis darauf nach, auch in Tooltips anderer Dokumente.
- Bewertet der Nutzer einen Punkt, etwa als „akzeptabel“, gilt das in allen Dokumenten des Themas. Ziehe Prüfbericht,
  TOP-Dokument, Antragstext und `NOTIZEN.md` nach.

## Prozesse

### Neues Projekt einrichten

Gilt für einen Projektordner, der noch nicht nach diesem Skill aufgebaut ist, etwa einen leeren Ordner oder einen
Ordner mit losen PDFs. Vor `git init` und vor dem Anlegen von Dateien in einem Ordner mit Inhalt fragst du den
Nutzer. Vorhandene Dokumente legst du danach einzeln ab (siehe Neues Dokument ablegen).

1. **Git:** Ist der Ordner kein Git-Repository, `git init`. Die `.gitignore` nennt `/tmp/` und `__pycache__/`.
2. **Ordner:** `Abrechnungen/`, `Versammlungen/`, `Verwaltung/` und `Stammdaten/` mit je einer `README.md`
   (Überschrift und ein Satz zum Inhalt), dazu `Vorgänge/Vorgänge.md` mit den Abschnitten „Laufend“ und „Archiv“
   und der Tabelle aus dem Abschnitt Vorgänge. Die `README.md` im Wurzelordner verlinkt alle Übersichten.
3. **`AGENTS.md`:** Frage den Nutzer nach den Angaben, die die Skills voraussetzen, und trage sie ein:
   - Objekt: Anschrift, Zahl der Einheiten
   - Einheiten des Nutzers: Nummer, Lage, Kennung bei der Verwaltung, MEA
   - Eigentümer und, wenn der Nutzer ihn vertritt, der Bevollmächtigte
   - Verwaltung mit Zeitraum und dem Präfix der Objektnummer in ihren Dateinamen, Messdienst der Heizkosten
   - bei vermieteter Einheit: Mieter, Beginn des Mietvertrags, Vorauszahlung, Verteilungsschlüssel
   - Verweise auf die Übersicht je Ordner
4. **`justfile`:** Ein Import je installiertem WEG-Skill:

   ```
   import '~/.claude/skills/weg-eigentuemer-ablage/scripts/ablage.just'
   import '~/.claude/skills/weg-abrechnung-pruefen/pruefen.just'
   import '~/.claude/skills/pdf-annotate/annotate.just'
   import '~/.claude/skills/etg24-portal/etg24.just'
   import '~/.claude/skills/weg-konten-belege/konten.just'
   import '~/.claude/skills/weg-vermieter-nebenkosten/nebenkosten.just'
   ```

5. **pre-commit-Hook:** `scripts/hooks/pre-commit` mit diesem Inhalt, ausführbar, dann
   `git config core.hooksPath scripts/hooks`:

   ```sh
   #!/bin/sh
   # Prüft vor jedem Commit den Arbeitsordner: Text-MDs aktuell, jedes Linkziel vorhanden, Fundstellen passend.
   cd "$(git rev-parse --show-toplevel)" || exit 1
   S="$HOME/.claude/skills/weg-eigentuemer-ablage/scripts"
   python3 "$S/pdf2md.py" --check --quiet && python3 "$S/check_links.py"
   ```

6. **SessionStart-Hook** (Claude Code): `.claude/settings.json` hält die Text-MDs bei jedem Start aktuell. Gibt es
   die Datei schon, fügst du den Hook dort ein.

   ```json
   {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "timeout": 600,
     "command": "cd \"$CLAUDE_PROJECT_DIR\" && python3 \"$HOME/.claude/skills/weg-eigentuemer-ablage/scripts/pdf2md.py\" --prune --quiet"}]}]}}
   ```

7. **Prüfen:** `just md`, dann `just qa`. Fertig ist die Einrichtung, wenn `just qa` nichts meldet.

### Neues Dokument ablegen

1. Dokument lesen (Scan ohne Textebene: `pdftoppm` und Seitenbilder ansehen oder OCR). Datum, Absender, Art,
   betroffene Einheit und Beträge bestimmen.
2. Ziel nach Ordnerstruktur wählen und Namen nach Konvention bilden. Bei Unklarheit den Nutzer fragen.
3. Prüfen, ob es das Dokument schon gibt: `just dup DATEI…` nennt zu jeder neuen Datei die gleiche in der Ablage.
4. Ablegen und eine Zeile eintragen (Pfad, was es ist, wichtigste Zahl oder Frist). Gehört das Dokument zu einem
   Vorgang, kommt die Zeile in dessen `NOTIZEN.md` unter „Dokumente“, sonst in die `README.md` des Hauptordners
   als relativer Link.
4a. Text-MD erzeugen: `just md-prune`. Danach liegt `X.md` neben `X.pdf`; bei OCR-Scans die Qualität kurz prüfen.
5. Fristen und Handlungsbedarf aus dem Dokument dem Nutzer nennen (siehe Fristen unten).

### Jahresabrechnung, Wirtschaftsplan, Beschlüsse oder Vertrag prüfen

Dafür gilt der Skill `weg-abrechnung-pruefen`.

### Kontoauszüge und Belege auswerten, Nebenkosten für den Mieter abrechnen

Kontoauszüge und Belege der Gemeinschaft überträgt der Skill `weg-konten-belege` in eine geprüfte Datenbasis. Die
Nebenkostenabrechnung für den Mieter einer vermieteten Einheit erstellt der Skill `weg-vermieter-nebenkosten`.

### Eigentümerversammlung vorbereiten

1. Einladung ablegen (`Versammlungen/JJJJMMTT Einladung Versammlung.pdf`). Einberufungsfrist prüfen: mindestens drei
   Wochen (§ 24 Abs. 4 WEG).
2. Jeden Tagesordnungspunkt mit Unterlagen verknüpfen (Abrechnung, Wirtschaftsplan, Angebote, Verträge) und die
   Möglichkeiten mit ihren Folgen nennen: Zustimmung, Ablehnung, Nachfrage. Die Vorbereitung liegt in
   `Versammlungen/JJJJMMTT Versammlung/`, mit einer `README.md` als Übersicht und einem eigenen Dokument je TOP mit
   viel Stoff. Hat ein TOP ein eigenes Dokument, fasst sein Abschnitt in der `README.md` unter dem Link die
   wichtigsten Punkte als Liste mit Quellenlinks zusammen. Die Liste übernimmt nur wichtige Punkte der
   Quelle, ohne eigene Zusätze. Ein Punkt aus einem Prüfbericht trägt seine Nummer als Link, etwa `[4.4](<…>)`.
   Jede Aussage steht in der `README.md` einmal. Gehört ein Punkt schon zu einem anderen TOP oder zu „Auffällig an
   allen TOPs“, verweist der Abschnitt dorthin. Ein TOP-Dokument hat die Abschnitte Befunde, Checkliste, Antragstext, Fragen an die Verwaltung und
   Hintergrund. Jeder Checklistenpunkt enthält die Stichpunkte, die man in der Versammlung braucht, als Unterpunkte
   direkt unter sich. Als eigener Text steht nur, was wörtlich vorgelesen wird: Änderungsantrag und Erklärung für
   das Protokoll. Sprechzettel, also ausformulierte Redebeiträge, gibt es nicht. Jede Aussage, die man in der
   Versammlung machen will, steht als Stichpunkt unter dem Checklistenpunkt, zu dem sie gehört.
   Steht eine Liste schon in einem
   Prüfbericht, etwa Änderungswünsche oder Befunde, verlinkt das TOP-Dokument sie mit ihrer Nummer, etwa „Prüfung Abr. 2025, Frage 4.2“. Eine Kopie
   veraltet, sobald der Prüfbericht sich ändert.
3. Eigene Anträge rechtzeitig vor der Einladung bei der Verwaltung einreichen, damit sie auf die Tagesordnung kommen.
4. Bei Abwesenheit: Vollmacht in Textform vorbereiten (§ 25 Abs. 3 WEG), ggf. mit Weisungen je TOP.
5. Nach der Versammlung: Protokoll und aktualisierte Beschluss-Sammlung ablegen und gegen eigene Notizen prüfen.
   Jeden Beschluss, der etwas umsetzt, als Vorgang aufnehmen oder beim bestehenden Vorgang nachtragen.
6. Anfechtung prüfen, falls ein Beschluss fehlerhaft erscheint: Klage binnen eines Monats nach Beschlussfassung,
   Begründung binnen zwei Monaten (§ 45 WEG). Frist dem Nutzer sofort nennen; rechtliche Bewertung einem Anwalt
   überlassen.

### Antrag an die Gemeinschaft stellen

Vorlage: Absender (Eigentümer, Einheit), Empfänger (Verwaltung), Betreff, Bitte um Aufnahme in die Tagesordnung
(alternativ Umlaufbeschluss, § 23 Abs. 3 WEG), **Sachverhalt**, **Beschlussvorschlag** (nummeriert, wörtlich
beschlussfähig), **Begründung**, Anlagen.

- Bauliche Veränderungen: Gestattung nach § 20 Abs. 1 WEG, Kosten und Folgekosten beim Antragsteller (§ 21 Abs. 1 WEG),
  Bedingungen (Fachbetrieb, Abnahme, Haftung, Genehmigungen, Termine) ausformulieren.
- Ablage als Markdown-Entwurf im Vorgang (`Vorgänge/<Vorgang>/Antrag/`), Platzhalter `[…]`
  kennzeichnen; die versandte Fassung als `JJJJMMTT Antrag ….pdf` ablegen.

### Schriftverkehr mit der Verwaltung

- Entwürfe sachlich, mit Bezug (Objekt, Einheit, Datum des Bezugsschreibens), konkreter Bitte und Frist.
- Versandte Schreiben und Antworten im Ordner der Verwaltung oder des Themas ablegen, mit Datum.
- Bei Pflichtverletzungen (fehlende Abrechnung, keine Versammlung) Fristen und Vertragsstellen aus dem
  Verwaltervertrag zitieren; Abmahnung oder Abberufung nur mit dem Beirat und dem Nutzer abstimmen.

### Vorgänge

Ein **Vorgang** ist ein Vorhaben, ein Ereignis mit langfristigen Folgen (z. B. ein Schadensfall) oder die Umsetzung
eines Beschlusses. Alle Vorgänge stehen in `Vorgänge/Vorgänge.md`. Das ist die einzige Übersicht: eine Tabellenzeile je
Vorgang mit Art, Start, Vorgang, nächstem Schritt und Frist, sortiert nach Art und Start. Der Abschnitt „Laufend“
enthält die offenen Vorgänge, der Abschnitt „Archiv“ die abgeschlossenen mit ihrem Ergebnis.

- **Art:** `PRV` für einen Vorgang, den der vertretene Eigentümer betreibt und bezahlt, auch wenn er einen
  WEG-Beschluss braucht (Beispiel: Balkonverglasung). `WEG` für einen Vorgang, den die Gemeinschaft beschließt und bezahlt und die
  Verwaltung ausführt (Beispiel: Rücklagenerhöhung, Schaden am Gemeinschaftseigentum).
- **Ordner oder Zeile:** Einen Ordner bekommt ein Vorgang mit mehreren Schritten, eigenen Dokumenten oder längerer
  Laufzeit. Eine kleine Umsetzung (Kündigung, Auftrag, Reparatur) steht nur als Zeile in `Vorgänge.md`.
- **Ordnername:** `Vorgänge/ART JJJJMM Kurzname/`. Der Monat ist der Beginn des Vorgangs bzw. der Monat des
  Ereignisses. Beispiele: `PRV 202305 Balkonverglasung/`, `WEG 202211 Wasserschaden/`.
- **Inhalt des Ordners:** `NOTIZEN.md` (Pflicht), bei Bedarf `TODO.md`, eigene Entwürfe, Anträge unter `Antrag/` und
  Dokumente, die nur zu diesem Vorgang gehören (Bauakte, Gutachten, Angebote, Schreiben der Versicherung).
  Abrechnungen, Protokolle, Verträge und die Prüfberichte dazu bleiben in `Abrechnungen/`, `Versammlungen/` und
  `Verwaltung/`. Die `NOTIZEN.md` nennt sie mit Pfad.
- **`NOTIZEN.md`:** Titel, Kopf mit Art und Start, dann die Abschnitte Ziel, Stand, Nächste Schritte, Beteiligte,
  Fristen, Dokumente. Ein Statusfeld gibt es nicht. Ob ein Vorgang abgeschlossen ist, zeigt der Ort `Archiv/`.
- **Verweise:** In `NOTIZEN.md` und `Vorgänge.md` ist jede genannte Datei, jeder Ordner und jeder andere Vorgang ein
  relativer Markdown-Link, z. B. `[Abrechnung 2025](<../../Abrechnungen/2025/Datei.pdf>)` oder
  `[WEG 202211 Wasserschaden](<../WEG 202211 Wasserschaden/NOTIZEN.md>)`. Der Pfad ist relativ zur Datei mit dem Link
  und steht in spitzen Klammern, weil Namen Leerzeichen enthalten. So sind die Links in VS Code, Obsidian und auf
  GitHub klickbar. Befehle (`just pdf`) und Platzhalter (`[…]`) bleiben in Backticks. Fertig ist ein Eintrag, wenn
  jedes Linkziel existiert.
- **Schadensfall:** Schadensmeldung, Gutachten, Zahlungen der Versicherung und Rechnungen liegen im Vorgang.
  Schadennummer, Versicherer und gezahlte Beträge stehen in der `NOTIZEN.md`. Beim Prüfen der Jahresabrechnung
  abgleichen, ob die Zahlungen gebucht sind.

Schritte:

1. **Anlegen:** Art und Startmonat bestimmen. Ordner mit `NOTIZEN.md` anlegen oder nur die Zeile vorsehen. Die Zeile
   in `Vorgänge.md` unter „Laufend“ einsortieren.
2. **Führen:** Bei jedem neuen Dokument oder Schritt die `NOTIZEN.md` (Stand, Nächste Schritte, Dokumente) und die
   Zeile in `Vorgänge.md` (nächster Schritt, Frist) nachziehen.
3. **Archivieren:** Ist das Ziel erreicht oder der Vorgang aufgegeben, den Nutzer fragen. Dann den Ordner unter
   gleichem Namen nach `Vorgänge/Archiv/` verschieben und die Zeile mit dem Ergebnis in den Abschnitt „Archiv“
   übernehmen. Danach `just md-prune` ausführen und Pfade in Verweisen (`README.md` der Ordner, Prüfberichte,
   `scripts/pdf2md-ignore.txt`) nachziehen. Eine Zeile ohne Ordner wandert nur in den Abschnitt „Archiv“.

### Skripte und Ausarbeitungen

- Skripte nach `scripts/`, Pfade relativ zum Projektordner (`Path(__file__).resolve().parent.parent`), Ausgabe beim
  Thema, Zwischenbilder nach `tmp/`.
- Ausgaben nach dem Erzeugen als Seitenbilder prüfen.

## Fristen im Blick

| Anlass | Frist | Grundlage |
|---|---|---|
| Einladung zur Versammlung | mind. 3 Wochen vorher | § 24 Abs. 4 WEG |
| Anfechtungsklage | 1 Monat nach Beschluss, Begründung 2 Monate | § 45 WEG |
| Nachschüsse aus Jahresabrechnung | Fälligkeit laut Beschluss | § 28 Abs. 2 WEG |
| Jahresabrechnung, Versammlung | laut Verwaltervertrag | Vertrag |

Fristen immer mit Datum dem Nutzer nennen und beim Vorgang vermerken (`Vorgänge.md` und `NOTIZEN.md`).
