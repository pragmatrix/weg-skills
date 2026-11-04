---
name: weg-konten-belege
description: Kontoauszüge und Belege einer WEG in eine geprüfte JSON-Datenbasis übertragen und gegen die Abrechnung abgleichen. Für Kontoauszüge der Gemeinschaft, Rechnungen und Buchungslisten der Verwaltung, den Abgleich der eigenen Hausgeldzahlungen und als Datenbasis einer Nebenkostenabrechnung für Mieter.
---

# Konten und Belege einer WEG

Der Nutzer ist Eigentümer oder Bevollmächtigter. Er hat Kontoauszüge der Gemeinschaft und Belege der Verwaltung,
etwa aus einer Belegeinsicht (§ 18 Abs. 4 WEG) oder einem Portal. Dieser Skill überträgt sie in eine **Datenbasis**
aus drei JSONs je Abrechnungsjahr und prüft sie doppelt: maschinell mit `pruefe_belege.py` und gegen die
Buchungslisten der Verwaltung als zweiten, unabhängigen Datensatz.

Die Datenbasis liegt in `Abrechnungen/JJJJ/` neben den Unterlagen:

| Datei | Inhalt |
|---|---|
| `konto_JJJJ.json` | alle Umsätze je Bankkonto und Auszug |
| `belege_JJJJ.json` | alle Belege mit Positionen, Querverweisen und offenen Punkten |
| `weg_abrechnung_JJJJ_weN.json` | Eckdaten der Einzelabrechnung von Einheit `N` |

Die Kontoauszüge liegen in `Abrechnungen/JJJJ/Konto/`, die Belege in `Abrechnungen/JJJJ/Belege/`. Schemata und
Namenskonventionen stehen in [schema.md](schema.md). Die Skripte hängen an diesen Namen.

**Überschneidung:** Die Checkliste Gesamtabrechnung im Skill `weg-abrechnung-pruefen` prüft Geldkonten, Sonderposten
und Deckung der Rücklage anhand der Abrechnung. Dieser Skill liefert dafür die Bankseite. Beide sollen später ggf. zu
einer Prüfung zusammengeführt werden. Bis dahin verweist der Prüfbericht auf die Datenbasis, statt ihre Zahlen
noch einmal herzuleiten.

## Werkzeuge

Die Rezepte liegen in `konten.just` neben dieser Datei. Die `justfile` des Projekts bindet sie ein mit
`import '.claude/skills/weg-konten-belege/konten.just'`. Fehlt der Import, trägst du ihn ein.

- `just konten JAHR` prüft die Datenbasis des Jahres: Saldo-Kette je Auszug, Jahresendsalden, Platzhalter,
  Buchungslisten, Positionssummen, Netto × (1 + MwSt.) = Brutto, die Paare unter `pruefungen`, byte-gleiche Belege
  und jede `fundstelle`. Exit-Code 1 heißt Fehler.
- `just zahlungen JAHR N` gleicht die Zahlungen von Einheit `N` laut Abrechnung mit den Kontoauszügen ab. Es meldet
  Zahlungen ohne Bankbeleg und Eingänge des Eigentümers, die in der Abrechnung fehlen.

Den Text eines PDFs liest du aus der Text-MD daneben (`X.pdf` → `X.md`, Skill `weg-eigentuemer-ablage`). Scans ohne
Textebene siehst du als Seitenbild an (`pdftoppm -png -r 110`, Ausgabe nach `tmp/`). Ein Foto in einer `.docx` liegt
nach `unzip` unter `word/media/`.

## Schritte

1. **Inventur.** Liste jedes PDF in `Konto/` und `Belege/` auf. Prüfe, ob zu jedem PDF mit Textebene eine Text-MD
   existiert (`just md`). Fertig ist der Schritt, wenn jedes Dokument entweder eine Text-MD hat oder als Scan
   erkannt ist.
2. **Eigenheiten lesen.** Lies den Abschnitt „Eigenheiten der Unterlagen“ der `Abrechnungen/README.md`. Er nennt den
   Aufbau der Kontoauszüge und Buchungslisten dieses Objekts. Fehlt eine Angabe, lerne den Aufbau an einem Muster je
   Dokumenttyp und trage ihn dort ein.
3. **JSONs schreiben** nach [schema.md](schema.md). Jeder Wert, der später in einen Bericht oder eine
   Nebenkostenabrechnung geht, bekommt eine `fundstelle`. Fehlt ein Auszug, trägst du einen Platzhalter ein.
4. **Maschinell prüfen** mit `just konten JAHR`. Fertig ist der Schritt bei Exit-Code 0, oder wenn jede Meldung als
   offener Punkt in `belege_JJJJ.json` steht.
5. **Gegen die Buchungslisten abgleichen.** Jede Bankbuchung hat ihr Gegenstück in der Buchungsliste der Verwaltung
   und umgekehrt. Ordne jede Rechnung ihrer Zahlung zu (Rechnungsnummer, Verwendungszweck). Jede Abweichung kommt
   unter `offene_punkte`.
6. **Eigene Zahlungen abgleichen** mit `just zahlungen JAHR N` für jede Einheit des Nutzers.
7. **Nachziehen.** Trage die Datenbasis mit einer Zeile in die `README.md` von `Abrechnungen/` ein (Jahr, Stand,
   Zahl der offenen Punkte). Nenne dem Nutzer die offenen Punkte nach Gewicht.

## Fallstricke

- **Retouren:** Eine Rücklastschrift fasst den geplatzten Betrag und das Bankentgelt in einem Betrag zusammen. Die
  Buchungsliste führt dieselbe Summe als negative Buchung.
- **Interne Umbuchungen** zwischen Rücklagen- und Girokonto erscheinen auf beiden Konten und werden beide Male
  erfasst.
- **Zahlbetrag und Rechnungsbetrag** können sich unterscheiden. Die Differenz kommt unter `offene_punkte`, die
  Belegdaten bleiben, wie sie im Beleg stehen.
- **Kontierung der Verwaltung:** Die Kontonummern einer Buchungsliste können falsch kontiert sein. Maßgeblich sind
  Partner und Verwendungszweck des Bankauszugs. Jede Abweichung kommt unter `offene_punkte`.
- **Heizung mit Vorrat:** Eine Position wie „Heizung mit Brennstoffzukauf“ rechnet Vorrat + Zukauf − Bestand +
  Wartung. Sie erscheint deshalb nicht 1:1 als Zahlung. Lieferungen nach dem Stichtag der Bestandsmessung gehören ins
  Folgejahr. Beide Sichten dokumentierst du, die Differenz ist eine Frage an die Verwaltung.
- **Bescheide des Vorjahres** im Belege-Ordner erfasst du nur, wenn im Jahr Zahlungen darauf laufen. Den
  Zusammenhang nennt die `anmerkung`.

## Abbruch

- Ein Scan ist unter etwa 150 dpi unleserlich: Bitte den Nutzer um einen besseren Scan.
- Eine Saldo-Kette löst sich nicht auf: Sie kommt als offener Punkt in `belege_JJJJ.json`, und die Prüfung gilt als
  nicht bestanden.
