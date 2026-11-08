---
name: weg-vermieter-nebenkosten
description: Nebenkostenabrechnung (Betriebskostenabrechnung) für den Mieter einer vermieteten Eigentumswohnung aus den WEG-Unterlagen erstellen oder prüfen. Für Umlagefähigkeit nach BetrKV, formelle Mindestangaben und Fristen, CO₂-Kostenaufteilung, Vorauszahlungen und die Abrechnung als PDF-Brief aus einer Typst-Vorlage.
---

# Nebenkostenabrechnung für den Mieter

Der Nutzer vermietet eine Einheit in einer WEG. Aus der Einzelabrechnung der WEG und der geprüften Datenbasis
(Skill `weg-konten-belege`) entsteht die Betriebskostenabrechnung des Mietverhältnisses. Erst entsteht eine
JSON-Datenbasis mit Begründungen, dann ein Entscheidungsdokument, zuletzt die Abrechnung als PDF-Brief.

Was für das Mietverhältnis gilt (Mieter, Mietvertrag, Vorauszahlung, Verteilungsschlüssel, Heizungsart, Wohnfläche),
steht in der `AGENTS.md` des Projekts und in `Vermietung/README.md`. Lies beide zuerst.

## Ablage

`Vermietung/` ist ein Hauptordner der Ablage (Skill `weg-eigentuemer-ablage`). Darin liegen `Mietvertrag/`, eine
`README.md` und ein Ordner je Abrechnungsjahr `JJJJ/` mit:

| Datei | Inhalt |
|---|---|
| `nebenkostenabrechnung_JJJJ_<Mieter>.json` | Datenbasis: Positionen mit Begründung, nicht aufgenommene Positionen, Summen, Entscheidungen, Folgeprüfungen |
| `Entscheidungen_Nebenkostenabrechnung_JJJJ.md` | Umlage-Tabelle, Entscheidungen, Folgeprüfungen, Unklarheiten |
| `JJJJMMTT Nebenkostenabrechnung JJJJ.pdf` | die versandte Fassung, als Scan oder als das verschickte PDF |

Das PDF, das `just nebenkosten` erzeugt, liegt in `tmp/` und gehört nicht in die Ablage. Es entsteht jederzeit neu aus
Vorlage und Datenbasis. Was der Mieter tatsächlich bekommen hat, belegt die abgelegte versandte Fassung. Eine
Unterschrift braucht die Abrechnung nicht, die Textform genügt (§ 126b BGB).

## Grundsätze

1. **WEG-Anteil und Mieter-Anteil sind verschieden.** Die Einzelabrechnung der WEG mischt Bewirtschaftung, Rücklage
   und Erhaltung. Jede Position wird einzeln auf Umlagefähigkeit geprüft (§ 556 BGB mit BetrKV).
2. **Jede Position hat eine Herkunft.** Das Feld `betrkv` nennt die Nummer der BetrKV. Das Feld `fundstelle` (siehe
   `schema.md` im Skill `weg-konten-belege`) nennt die Stelle im Beleg, oder `berechnung` nennt den Rechenweg.
   Jede umlagefähige Position braucht `betrkv` und dazu `fundstelle` oder `berechnung`, sonst bricht
   `just nebenkosten` ab.
3. **Nicht umlagefähige Positionen werden dokumentiert**, mit Begründung unter `nicht_aufgenommen`.
4. **Platzhalter tragen eine `warnung`:** ein Wert ohne Beleg im Jahr, etwa Grundsteuer ohne Bescheid oder CO₂ ohne
   Literangabe. Jeder Platzhalter steht auch unter `folgepruefungen`.
5. **Die Abrechnung ist ein Entwurf.** Der Nutzer versendet sie, nachdem jeder offene Punkt geklärt ist.

## Gesetzliche Anforderungen

Fehlt einer Abrechnung eine **Mindestangabe**, ist sie formell unwirksam. Geht bis zum Ende der Abrechnungsfrist
keine formell ordnungsgemäße Abrechnung zu, ist die Nachforderung ausgeschlossen. Ein Formfehler kostet also das
Ergebnis, auch wenn jeder Betrag stimmt. `just nebenkosten` prüft deshalb die Mindestangaben, bevor es das PDF
erzeugt.

Mindestangaben nach ständiger Rechtsprechung des BGH (Urteil vom 29.01.2020, VIII ZR 244/18):

| Mindestangabe | In der Abrechnung | In der Datenbasis |
|---|---|---|
| Gesamtkosten je Kostenart | Spalte „Gesamtkosten“ | `gesamtkosten` je Position |
| Verteilerschlüssel, erläutert, wo er nicht aus sich heraus verständlich ist | Spalte „Verteilerschlüssel“, Erläuterung vor dem Schlusstext | `schluessel` je Position, `verteilvermerk` |
| Berechnung des Anteils des Mieters | Spalte „Ihr Anteil“ | `betrag` je Position |
| Abzug der Vorauszahlungen | Zeile „Ihre Vorauszahlung“ | `summen.vorauszahlung` |

- **Gesamtkosten** sind der Betrag, der je Kostenart auf die Abrechnungseinheit umgelegt wird. Bei einer WEG mit
  einem Gebäude sind das die Gesamtkosten der Gemeinschaft laut Einzelabrechnung der WEG. Ein vorab um nicht
  umlagefähige Anteile bereinigter Betrag genügt, die Rechenschritte dahin muss die Abrechnung nicht zeigen (BGH,
  Urteil vom 20.01.2016, VIII ZR 93/15).
- **Verteilerschlüssel:** Formell fehlerhaft ist ein fehlender oder unverständlicher Schlüssel (BGH, Urteil vom
  09.04.2008, VIII ZR 84/07). Eine Erläuterung braucht er nur ausnahmsweise, „Fläche“ und „Miteigentumsanteile“
  verstehen sich von selbst (VIII ZR 244/18). Ein anderer als der vereinbarte Schlüssel, etwa Anteile statt
  Wohnfläche, ist nur ein inhaltlicher Fehler und wird korrigiert (BGH, Urteil vom 17.11.2004, VIII ZR 115/04).
- **Teilbarkeit:** Betrifft ein Formfehler nur einzelne Positionen, die sich unschwer herausrechnen lassen, bleibt
  die Abrechnung im Übrigen wirksam. Zieht er sich durch die ganze Abrechnung, ist sie insgesamt unwirksam (BGH,
  Urteil vom 18.05.2011, VIII ZR 240/10).
- **Messdienst:** Verteilt ein Messdienst Heiz- und Wasserkosten, liegt seine Heizkostenabrechnung der Abrechnung als
  Anlage bei, und zwar vollständig. Sie trägt Gesamtkosten und Verteilung dieser Positionen, der Schlüssel in der
  Tabelle verweist auf sie. Sie enthält außerdem die Angaben zur CO₂-Aufteilung nach § 7 Abs. 3 CO2KostAufG und die
  Abrechnungs- und Verbrauchsinformationen nach § 6a HeizkV mit Anlage 2, die der Mieter bekommen muss. Weitere
  Pflichtanlagen gibt es nicht. Belege wie Bescheide und Rechnungen sieht der Mieter auf Wunsch ein (Belegeinsicht).
- **`verteilvermerk`** ist an den Mieter gerichtet. Er sagt, was jeder Schlüssel bedeutet und welcher Anteil auf die
  Wohnung entfällt, etwa „MEA = Miteigentumsanteile laut Teilungserklärung (Ihre Wohnung 250 von 1000)“.

Fristen und Rechte:

- **Abrechnungsfrist:** Die Abrechnung muss dem Mieter spätestens zwölf Monate nach Ende des Abrechnungszeitraums
  zugehen (§ 556 Abs. 3 Satz 2 und 3 BGB). Danach ist eine Nachforderung ausgeschlossen, außer der Vermieter hat die
  Verspätung nicht zu vertreten. Der Abrechnungszeitraum umfasst höchstens ein Jahr. Den Zugang belegen ein Bote oder
  ein Einwurf-Einschreiben.
- **Einwendungen des Mieters:** bis zwölf Monate nach Zugang der Abrechnung (§ 556 Abs. 3 Satz 5 und 6 BGB).
- **Vereinbarung:** Umlegbar sind nur Kosten, die der Mietvertrag dem Mieter auferlegt (§ 556 Abs. 1 BGB). Die
  Vereinbarung, dass der Mieter „die Betriebskosten“ trägt, erfasst alle Kosten der BetrKV außer den sonstigen
  Betriebskosten nach § 2 Nr. 17, die einzeln genannt sein müssen (BGH, Urteil vom 10.02.2016, VIII ZR 137/15). Eine
  nicht vereinbarte Position ist ein inhaltlicher Fehler, kein formeller (VIII ZR 240/10).
- **Wirtschaftlichkeit:** Umlegbar ist nur, was eine ordentliche Bewirtschaftung erfordert (§ 556 Abs. 3 Satz 1
  BGB). Eine Doppelversicherung oder doppelt gebuchte Kosten verletzen das.
- **Belegeinsicht:** Der Mieter darf die Belege einsehen. Bei einer vermieteten Eigentumswohnung beschafft der
  Vermieter sie bei der Verwaltung.
- **Kürzungsrechte des Mieters:**
  - 15 % des Anteils, der entgegen der HeizkV nicht nach Verbrauch abgerechnet ist (§ 12 Abs. 1 HeizkV). Das gilt nur
    für den betroffenen Teil, etwa nur das Warmwasser. Zwischen Eigentümer und Gemeinschaft gilt es nicht.
  - 3 % der Heizkosten, wenn die Abrechnung den CO₂-Anteil oder die Angaben nach § 7 Abs. 3 CO2KostAufG nicht
    ausweist (§ 7 Abs. 4 CO2KostAufG). Für falsch berechnete Angaben ist das umstritten.
  - Beide Kürzungen macht der Mieter geltend, sie wirken nicht von selbst.

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
| Baumfällung eines kranken oder nicht mehr standsicheren Baums, Erneuerung von Pflanzen und Gehölzen | ja | § 2 Nr. 10, für das Fällen eines kranken Baums BGH, Urteil vom 10.11.2021, VIII ZR 107/20 |
| Baumfällung für einen Umbau oder eine Umgestaltung | nein | keine Gartenpflege, sondern Aufwand des Eigentümers |
| Baumfällung mit unklarem Anlass | vorläufig ja | `umlagefaehig: true` mit `warnung` und Folgeprüfung, den Anlass klärt die Verwaltung |
| Neuanlage oder Umgestaltung des Gartens | nein | keine Pflege, sondern Herstellung oder Modernisierung |
| Verwaltervergütung, Bankspesen, Porto | nein | Verwaltungskosten |
| Zuführung zur Rücklage, Sonderumlage | nein | Aufwand des Eigentümers |
| Restforderung oder Abschlussausgleich eines Versorgers | nein | schon in der Jahreskostenposition enthalten |

## Steuerermäßigung nach § 35a EStG

Der Mieter kann 20 % der Arbeitskosten für haushaltsnahe Dienstleistungen (§ 35a Abs. 2 EStG) und Handwerkerleistungen
(§ 35a Abs. 3 EStG) von der Steuer abziehen, die in seinen Betriebskosten stecken. Eine Mindestangabe ist das nicht,
Mieter fragen aber oft danach. Die Abrechnung nennt die Beträge deshalb, sobald eine Position das Feld `steuer_35a`
trägt.

- **Begünstigt** sind nur Arbeitskosten mit Fahrtkosten, unbar bezahlt. Haushaltsnahe Dienstleistungen sind etwa
  Gartenpflege, Hausreinigung, Hausmeister und Winterdienst. Handwerkerleistungen sind etwa Schornsteinfeger mit
  Kehr- und Messarbeiten und die Wartung von Heizung und Rauchmeldern.
- **Nicht begünstigt** sind Material, Gebühren, Energie, Wasser, Versicherungen, Grundsteuer und das Ablesen und
  Abrechnen der Verbrauchszähler.
- **Quelle** ist die Zusammenstellung nach § 35a EStG in der Einzelabrechnung der WEG. Fehlt sie oder trennt die
  Rechnung Lohn und Material nicht, ist die Rechnung die Quelle.
- **Nicht umlagefähige Positionen** wie Instandhaltung stehen oft in derselben Zusammenstellung. Sie gehören nicht
  in die Abrechnung des Mieters.

## CO₂-Kosten

Die Aufteilung folgt dem **Stufenmodell** der Anlage zum CO2KostAufG (§ 5), nie einer Pauschale. Die Stufe gilt für
das ganze Gebäude. Liter und Wohnfläche sind deshalb die des Gebäudes, nie der Anteil der Einheit. Nennt die
Heizkostenabrechnung des Messdienstes die Stufe oder den CO₂-Ausstoß je m², gilt diese Angabe.

```
Gesamtliter Heizöl des Gebäudes × 2,664 kg CO₂/l ÷ Gesamtwohnfläche des Gebäudes (m²)
  → kg CO₂/m²/a → Stufe → Anteil Mieter und Vermieter
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
die Liter und die Wohnfläche des Gebäudes gibt es keine Berechnung. Bis dahin steht der Vorjahresbetrag als
Platzhalter mit `warnung`, und die Lieferscheine werden bei der Verwaltung angefordert.

## PDF aus der Vorlage

Die Abrechnung ist ein Brief nach DIN 5008 Form B. Die Typst-Vorlage `nebenkostenabrechnung.typ` neben dieser Datei
setzt ihn aus der Datenbasis. Sie gilt für jedes Jahr und jedes Mietverhältnis und enthält keine Angaben zu einem
Objekt. Anschrift und Rücksendeangabe sitzen im Fenster eines DL- oder C5/6-Kuverts, dazu kommen Falz- und Lochmarken.
Die Positionstabelle trägt die Mindestangaben in den Spalten Kostenart, Verteilerschlüssel, Gesamtkosten und Ihr
Anteil. Darunter folgen Summe, Vorauszahlung und Ergebnis, dann der `verteilvermerk`, die Angabe nach § 35a EStG
und der Gruß. Ist das Ergebnis negativ, heißt die Zeile „Ihr Guthaben“ und zeigt den Betrag positiv. Solange eine
Position eine `warnung` trägt, steht „ENTWURF“ hinter dem Text.

Die Vorlage rechnet nichts neu, sie übernimmt Beträge und Summen aus der Datenbasis. Vorher prüft sie die
Mindestangaben, die Herkunft jeder umlagefähigen Position und `umlagefaehig` als `true` oder `false` an jeder
Position. Sie prüft auch, dass der Abrechnungszeitraum im Abrechnungsjahr liegt und `datum_abrechnung` danach.
Außerdem prüft sie, dass die Positionen die Summe ergeben und Summe minus Vorauszahlung das Ergebnis. Bei einem Befund
bricht sie mit der Liste aller Befunde ab, und es entsteht kein PDF.

Das Rezept liegt in `nebenkosten.just` neben dieser Datei und ruft `scripts/nebenkosten.sh` auf. Die `justfile` des
Projekts bindet es ein mit `import '.claude/skills/weg-vermieter-nebenkosten/nebenkosten.just'`. Es braucht `typst`
ab Version 0.15, `python3` und `pdfunite` aus Poppler. Die Vorlage setzt Arial. Fehlt die Schrift, nimmt Typst
mit einer Warnung eine eigene.

- `just nebenkosten JAHR` liest die eine Datei `nebenkostenabrechnung_JAHR_*.json` in `Vermietung/JAHR/`, prüft sie
  und schreibt `tmp/Nebenkostenabrechnung JAHR.pdf`. Die Dateien unter `anlagen` hängt es in dieser Reihenfolge an
  den Brief an. Fehlt eine, bricht es ab. Exit-Code 0 heißt bestanden.

## Schritte

1. **Datenbasis prüfen.** Die Datenbasis der WEG des Jahres hat `just konten JAHR` bestanden (Skill
   `weg-konten-belege`). Fertig ist der Schritt, wenn jede Meldung als offener Punkt dokumentiert ist.
2. **Positionen ableiten.** Entscheide für jede Kostenposition der Einzelabrechnung die Umlagefähigkeit nach der
   Tabelle. Begründe den Verteilungsschlüssel (MEA, Fläche, Einheiten). Gebühren mit eigenem Maßstab gibst du mit
   diesem Maßstab weiter, etwa Niederschlagswasser nach versiegelter Fläche oder Einheiten statt nach Verbrauch.
   Fertig ist der Schritt, wenn jede Kostenposition der Einzelabrechnung entschieden ist, als umlagefähig mit
   BetrKV-Nummer, Gesamtkosten und Verteilungsschlüssel oder als nicht umlagefähig mit Begründung.
3. **Vorauszahlungen** des Mieters ansetzen, laut Mietvertrag und Zahlungseingang. Das Hausgeld der WEG zählt hier
   nicht. Fertig ist der Schritt, wenn der Betrag den Zahlungseingängen des Jahres entspricht oder die Abweichung
   unter `folgepruefungen` steht.
4. **JSON schreiben.** Jede Position hat `position`, `betrag`, `betrkv`, `umlagefaehig`, `fundstelle` bzw.
   `berechnung` und bei Bedarf `warnung`. Jede umlagefähige Position hat dazu `gesamtkosten` und `schluessel`, einen
   kurzen Text für die Spalte, etwa „MEA 250 von 1000“. Dazu kommen `datum_abrechnung` (JJJJ-MM-TT, nach dem
   Abrechnungsjahr), `verteilvermerk`, `nicht_aufgenommen`, `summen` mit `summe_betriebskosten`, `vorauszahlung` und
   `nachzahlung` (negativ bei einem Guthaben), `entscheidungen`, `folgepruefungen` und `verifizierungsfragen`.
   Für den Brief braucht die Vorlage außerdem diese Felder:

   | Feld | Inhalt | Beispiel |
   |---|---|---|
   | `jahr` | Abrechnungsjahr als Zahl | `2025` |
   | `vermieter.name`, `vermieter.adresse` | Absender, Anschrift als „Straße, PLZ Ort“ | „Musterstraße 1, 12345 Musterstadt“ |
   | `mieterin.name`, `mieterin.adresse` | Empfänger, Anschrift wie beim Vermieter | |
   | `mieterin.wohnung` | Lage der Wohnung für den Betreff. Ein Zusatz in Klammern erscheint dort nicht. | „EG links (Einheit 3, 250/1000 MEA)“ |
   | `mieterin.mietvertrag_vom` | optional, Datum des Mietvertrags für den Betreff | `2020-04-01` |
   | `mieterin.anrede` | optional, die ganze Anrede mit Komma. Ohne das Feld steht „Sehr geehrte Damen und Herren,“. | „Sehr geehrte Frau Beispiel,“ |
   | `abrechnungszeitraum.von`, `abrechnungszeitraum.bis` | Abrechnungszeitraum im Abrechnungsjahr, bei einem Mieterwechsel der Teil des Jahres | `2025-01-01`, `2025-12-31` |
   | `anlagen` | optional, Liste der Anlagen mit `bezeichnung` für den Anlagenvermerk und `datei`, dem Pfad einer PDF-Datei relativ zum Projektordner | `[{"bezeichnung": "Heizkostenabrechnung 2025", "datei": "Abrechnungen/2025/Heizkostenabrechnung.pdf"}]` |
   | `positionen[].steuer_35a` | optional, je Position: `art` („haushaltsnah“ oder „handwerker“), `betrag` (Arbeitskosten im Anteil des Mieters) und `fundstelle` oder `berechnung` | `{"art": "handwerker", "betrag": 12.50, "fundstelle": "Abrechnung.pdf, S. 7"}` |

   Die Anrede schreibst du nur, wenn sie aus dem Mietvertrag oder einer früheren Abrechnung hervorgeht. Aus dem
   Namen leitest du sie nicht ab.
   Fertig ist der Schritt, wenn `python3 -m json.tool` die Datei ohne Fehler liest und jede Kostenposition aus Schritt 2
   unter `positionen` oder `nicht_aufgenommen` steht.
5. **Entscheidungsdokument** schreiben, mit Umlage-Tabelle, Entscheidungen, Checkliste der Folgeprüfungen und
   Unklarheiten. Es folgt den Regeln zu Quellenlinks und Gliederung im Skill `weg-eigentuemer-ablage`. Fertig ist es,
   wenn `just qa` nichts mehr meldet.
6. **PDF bauen** mit `just nebenkosten JAHR`. Fertig ist der Schritt bei Exit-Code 0. Ein PDF mit Platzhaltern trägt
   den Vermerk ENTWURF und geht so nicht an den Mieter.
7. **Vor dem Versand** nennst du dem Nutzer, was noch gegen einen Beleg zu prüfen ist: Grundsteuerbescheid,
   CO₂-Literangabe, Abrechnungsfrist mit Datum und Nachweis des Zugangs (Abschnitt Gesetzliche Anforderungen), die
   Heizkostenabrechnung des Messdienstes unter `anlagen`. Dazu kommt eine Anpassung der Vorauszahlung, wenn die
   Nachzahlung hoch ist (§ 560 Abs. 4 BGB).
8. **Nachziehen.** Trage die Abrechnung mit einer Zeile in `Vermietung/README.md` ein (Pfad, Ergebnis, Frist). Hat
   der Nutzer sie versandt, legst du die versandte Fassung als `JJJJMMTT Nebenkostenabrechnung JJJJ.pdf` im
   Jahresordner ab, mit dem Datum des Versands.

## Fallstricke

- **Brennstoff mit Vorrat:** Die WEG rechnet Vorrat + Zukauf − Bestand. Zahlungen für Lieferungen nach dem Stichtag
  gehören ins Folgejahr. Beide Sichten stehen in der Datenbasis, die Differenz ist eine Frage an die Verwaltung.
- **Wasser im Messdienst:** Hat die WEG-Abrechnung kein eigenes Wasserkonto, verteilt meist der Messdienst das Wasser
  mit den Heizkosten. Ohne Heizkostenabrechnung des Messdienstes wird Wasser nicht eigens angesetzt. Ihre
  Kostenaufstellung zeigt, ob Frisch- und Abwasser darin stecken. Eine Wasserzeile der Abrechnung des Vorjahres
  bleibt nur, wenn die WEG-Abrechnung das Wasser auch in diesem Jahr getrennt führt.
- **Fälligkeit und Entstehung:** Bescheide für ein Jahr kommen oft erst im Folgejahr. Die Abrechnung weist die Kosten
  im Jahr aus, für das sie entstehen.
- **Platzhalter brauchen eine Herkunft:** Auch eine Position mit `warnung` nennt in `berechnung`, woher der Wert
  stammt, etwa „Vorjahresbetrag laut Abrechnung JJJJ“. Sonst bricht `just nebenkosten` ab.

## Abbruch

- Der Verteilungsschlüssel im Mietvertrag ist unklar (Wohnfläche oder Anteile): Frage den Nutzer.
- Liter oder Wohnfläche des Gebäudes fehlen: Die CO₂-Position steht nur als Platzhalter mit `warnung` und
  Folgeprüfung in der Abrechnung.
- Der Grundsteuerbescheid fehlt: Der Vorjahresbetrag steht nur mit `warnung` in der Abrechnung, und vor dem Versand
  wird er gegen den Bescheid geprüft.
