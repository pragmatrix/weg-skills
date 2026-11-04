---
name: weg-vermieter-nebenkosten
description: Nebenkostenabrechnung (Betriebskostenabrechnung) für den Mieter einer vermieteten Eigentumswohnung aus den WEG-Unterlagen erstellen. Für Umlagefähigkeit nach BetrKV, CO₂-Kostenaufteilung, Vorauszahlungen und die Excel-Abrechnung im Layout des Vorjahres.
---

# Nebenkostenabrechnung für den Mieter

Der Nutzer vermietet eine Einheit in einer WEG. Aus der Einzelabrechnung der WEG und der geprüften Datenbasis
(Skill `weg-konten-belege`) entsteht die Betriebskostenabrechnung des Mietverhältnisses. Erst entsteht eine
JSON-Datenbasis mit Begründungen, dann ein Entscheidungsdokument, zuletzt die Excel-Abrechnung im Layout des Vorjahres.

Was für das Mietverhältnis gilt (Mieter, Mietvertrag, Vorauszahlung, Verteilungsschlüssel, Heizungsart, Wohnfläche),
steht in der `AGENTS.md` des Projekts und in `Vermietung/README.md`. Lies beide zuerst.

## Ablage

`Vermietung/` ist ein Hauptordner der Ablage (Skill `weg-eigentuemer-ablage`). Darin liegen `Mietvertrag/`, eine
`README.md` und ein Ordner je Abrechnungsjahr `JJJJ/` mit:

| Datei | Inhalt |
|---|---|
| `nebenkostenabrechnung_JJJJ_<Mieter>.json` | Datenbasis: Positionen mit Begründung, nicht aufgenommene Positionen, Summen, Entscheidungen, Folgeprüfungen |
| `Entscheidungen_Nebenkostenabrechnung_JJJJ.md` | Umlage-Tabelle, Entscheidungen, Folgeprüfungen, Unklarheiten |
| `<Name der Vorlage mit neuem Jahr>.xlsx` | die Abrechnung |
| `JJJJMMTT Nebenkostenabrechnung JJJJ.pdf` | die versandte Fassung |

## Grundsätze

1. **WEG-Anteil und Mieter-Anteil sind verschieden.** Die Einzelabrechnung der WEG mischt Bewirtschaftung, Rücklage
   und Erhaltung. Jede Position wird einzeln auf Umlagefähigkeit geprüft (§ 556 BGB mit BetrKV).
2. **Jede Position hat eine Fundstelle:** BetrKV-Nummer und Herkunft in der Datenbasis als Feld `fundstelle` (siehe
   `schema.md` im Skill `weg-konten-belege`).
3. **Nicht umlagefähige Positionen werden dokumentiert**, mit Begründung unter `nicht_aufgenommen`.
4. **Platzhalter tragen eine `warnung`:** ein Wert ohne Beleg im Jahr, etwa Grundsteuer ohne Bescheid oder CO₂ ohne
   Literangabe. Jeder Platzhalter steht auch unter `folgepruefungen`.
5. **Die Abrechnung ist ein Entwurf.** Der Nutzer versendet sie, nachdem jeder offene Punkt geklärt ist.

## Umlagefähigkeit

| WEG-Position | Umlagefähig | Fundstelle |
|---|---|---|
| Grundsteuer | ja | § 2 Nr. 1 BetrKV |
| Wasser, Schmutzwasser, Niederschlagswasser | ja | § 2 Nr. 2 und 3 |
| Allgemeinstrom | ja | § 2 Nr. 11 |
| Heiz- und Brennstoffkosten | ja | § 2 Nr. 4a bzw. 6a |
| Schornsteinfeger (Prüfung, Messung) | ja | § 2 Nr. 4a bzw. 12 |
| Gebäude- und Haftpflichtversicherung | ja | § 2 Nr. 13 |
| Müllgebühren | ja | § 2 Nr. 8 |
| Gartenpflege, nur die gärtnerische Pflege | ja | § 2 Nr. 10 |
| Instandhaltung, Reparaturen, Schadenssanierung | nein | Vermietersache (§ 535 BGB) |
| Baumfällung, Erneuerung von Gehölzen | nein | fällt nicht unter Nr. 10 |
| Verwaltervergütung, Bankspesen, Porto | nein | Verwaltungskosten |
| Zuführung zur Rücklage, Sonderumlage | nein | Aufwand des Eigentümers |
| Restforderung oder Abschlussausgleich eines Versorgers | nein | schon in der Jahreskostenposition enthalten |

## CO₂-Kosten

Die Aufteilung folgt dem **Stufenmodell** der Anlage zum CO2KostAufG (§ 5), nie einer Pauschale.

```
Liter Heizöl × 2,664 kg CO₂/l ÷ Wohnfläche (m²) → kg CO₂/m²/a → Stufe → Anteil Mieter und Vermieter
```

Der Faktor 2,664 kg CO₂ je Liter ergibt sich aus 10 kWh je Liter × 0,2664 kg CO₂ je kWh. Die oft genannten 3,17 kg
gelten je Kilogramm Heizöl, nicht je Liter.

| kg CO₂/m²/a | Mieter | Vermieter |
|---|---|---|
| < 12 | 100 % | 0 % |
| 12 bis < 17 | 90 % | 10 % |
| 17 bis < 22 | 80 % | 20 % |
| 22 bis < 27 | 70 % | 30 % |
| 27 bis < 32 | 60 % | 40 % |
| 32 bis < 37 | 50 % | 50 % |
| 37 bis < 42 | 40 % | 60 % |
| 42 bis < 47 | 30 % | 70 % |
| 47 bis < 52 | 20 % | 80 % |
| ≥ 52 | 5 % | 95 % |

Den CO₂-Preis nach BEHG für das Abrechnungsjahr schlägst du nach (2025: 55 €/t, rund 0,15 € je Liter Heizöl). Ohne
Liter und Wohnfläche gibt es keine Berechnung. Bis dahin steht der Vorjahresbetrag als Platzhalter mit `warnung`, und
die Lieferscheine werden bei der Verwaltung angefordert.

## Template-Verfahren

Die Excel-Abrechnung entsteht aus der Abrechnung des Vorjahres als **Vorlage**. Das Skript ersetzt nur Zellinhalte,
also Positionen, Summen, Titel, Datum und Jahreszahlen. Zeilenhöhen, Formate, verbundene Zellen, Formeln und
Seitenlayout bleiben so erhalten, wie der Mieter sie kennt. Ein Nachbau des Layouts verliert diese Details, auch wenn
der Zellvergleich gleich aussieht.

Die Rezepte liegen in `nebenkosten.just` neben dieser Datei. Die `justfile` des Projekts bindet sie ein mit
`import '~/.claude/skills/weg-vermieter-nebenkosten/nebenkosten.just'`.

- `just nebenkosten JAHR [VORLAGE]` baut die Abrechnung. Ohne Vorlage nimmt es die `*Nebenkostenabrechnung*.xlsx` in
  `Vermietung/<JAHR-1>/`. Liegt dort nur eine `.xls`, bricht es ab. Der Nutzer konvertiert sie dann einmal in Excel
  oder Numbers nach `.xlsx`.
- `just nebenkosten-pruefen JAHR [VORLAGE]` prüft Positionen, Summe, Vorauszahlung und Nachzahlung gegen die
  Datenbasis und das Format gegen die Vorlage. Exit-Code 0 heißt bestanden.

Beide brauchen `openpyxl`. Sie laufen mit dem Python eines venv in `$TMPDIR`
(`python3 -m venv "$TMPDIR/nk-venv" && "$TMPDIR/nk-venv/bin/pip" install openpyxl`). Dann ruft man sie als
`PYTHON="$TMPDIR/nk-venv/bin/python" just nebenkosten …`. openpyxl schreibt Formeln ohne berechneten Wert. Summe und
Nachzahlung erscheinen erst beim Öffnen in Excel oder Numbers, deshalb rechnet das Prüfskript sie selbst nach.

## Schritte

1. **Datenbasis prüfen.** Die Datenbasis der WEG des Jahres hat `just konten JAHR` bestanden (Skill
   `weg-konten-belege`). Fertig ist der Schritt, wenn jede Meldung als offener Punkt dokumentiert ist.
2. **Positionen ableiten.** Entscheide für jede Kostenposition der Einzelabrechnung die Umlagefähigkeit nach der
   Tabelle. Begründe den Verteilungsschlüssel (MEA, Fläche, Einheiten). Gebühren mit eigenem Maßstab gibst du mit
   diesem Maßstab weiter, etwa Niederschlagswasser nach versiegelter Fläche oder Einheiten statt nach Verbrauch.
3. **Vorauszahlungen** des Mieters ansetzen, laut Mietvertrag und Zahlungseingang. Das Hausgeld der WEG zählt hier
   nicht.
4. **JSON schreiben.** Jede Position hat `position`, `betrag`, `betrkv`, `umlagefaehig`, `fundstelle` bzw.
   `berechnung` und bei Bedarf `warnung`. Dazu kommen `nicht_aufgenommen`, `summen` mit `vorauszahlung`,
   `entscheidungen`, `folgepruefungen` und `verifizierungsfragen`. Prüfe die Syntax mit `python3 -m json.tool`.
5. **Entscheidungsdokument** schreiben, mit Umlage-Tabelle, Entscheidungen, Checkliste der Folgeprüfungen und
   Unklarheiten. Es folgt den Regeln zu Quellenlinks und Gliederung im Skill `weg-eigentuemer-ablage`. Fertig ist es,
   wenn `just qa` nichts mehr meldet.
6. **Excel bauen**, sobald jeder Platzhalter geklärt oder bewusst als Übergang beibehalten ist. Erst
   `just nebenkosten JAHR`, dann `just nebenkosten-pruefen JAHR`. Fertig ist der Schritt bei Exit-Code 0.
7. **Vor dem Versand** nennst du dem Nutzer, was noch gegen einen Beleg zu prüfen ist: Grundsteuerbescheid,
   CO₂-Literangabe, Abrechnungsfrist von zwölf Monaten nach Ende des Abrechnungszeitraums (§ 556 Abs. 3 BGB). Dazu
   kommt eine Anpassung der Vorauszahlung, wenn die Nachzahlung hoch ist (§ 560 Abs. 4 BGB).
8. **Nachziehen.** Trage die Abrechnung mit einer Zeile in `Vermietung/README.md` ein (Pfad, Ergebnis, Frist).

## Fallstricke

- **Brennstoff mit Vorrat:** Die WEG rechnet Vorrat + Zukauf − Bestand. Zahlungen für Lieferungen nach dem Stichtag
  gehören ins Folgejahr. Beide Sichten stehen in der Datenbasis, die Differenz ist eine Frage an die Verwaltung.
- **Wasser im Messdienst:** Hat die WEG-Abrechnung kein eigenes Wasserkonto, verteilt meist der Messdienst das Wasser
  mit den Heizkosten. Ohne Heizkostenabrechnung des Messdienstes wird Wasser nicht eigens angesetzt. Ihre
  Kostenaufstellung zeigt, ob Frisch- und Abwasser darin stecken. Eine Wasserzeile aus der Vorlage des Vorjahres
  bleibt nur, wenn die WEG-Abrechnung das Wasser auch in diesem Jahr getrennt führt.
- **Fälligkeit und Entstehung:** Bescheide für ein Jahr kommen oft erst im Folgejahr. Die Abrechnung weist die Kosten
  im Jahr aus, für das sie entstehen.
- **Endsummen fett** wie in der Vorlage. Das Template-Verfahren erhält das, das Prüfskript kontrolliert Fonts und
  Zahlenformate der Ankerzellen.

## Abbruch

- Der Verteilungsschlüssel im Mietvertrag ist unklar (Wohnfläche oder Anteile): Frage den Nutzer.
- Liter oder Wohnfläche fehlen: Die CO₂-Position steht nur als Platzhalter mit `warnung` und Folgeprüfung in der
  Abrechnung.
- Der Grundsteuerbescheid fehlt: Der Vorjahresbetrag steht nur mit `warnung` in der Abrechnung, und vor dem Versand
  wird er gegen den Bescheid geprüft.
