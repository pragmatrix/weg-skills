# JSON-Schemata der Datenbasis

Die Datenbasis eines Abrechnungsjahres besteht aus drei JSONs in `Abrechnungen/JJJJ/`. Die Schemata sind
konventionell, nicht strikt. Pflicht sind die Felder, die ein Prüfskript braucht. Alles andere ist Dokumentation für
Menschen und Agenten. Beträge stehen als Zahl mit Punkt, Daten als ISO-Datum (`JJJJ-MM-TT`).

## Fundstelle

Jedes Objekt darf ein Feld `fundstelle` tragen. Es nennt, wo der Wert im Original steht, damit ein Bericht daraus
einen Quellenlink bilden kann.

```jsonc
"fundstelle": { "datei": "Abrechnungen/2025/Konto/<PDF>", "seite": 3, "position": "Buchung 05.08.2025" }
```

- `datei` ist der Pfad relativ zum Projektordner.
- `seite` ist die Seite der PDF-Datei, gezählt wie bei Quellenlinks (Skill `weg-abrechnung-pruefen`, Abschnitt
  „Belege“).
- `position` ist frei und nennt Zeile, Buchung oder Posten.

`pruefe_belege.py` prüft jede `fundstelle` in allen drei JSONs. Die Datei muss existieren, und die Seite muss im PDF
liegen. Ein Feld `quelle` ist dagegen freie Dokumentation und wird nicht geprüft.

## konto_JJJJ.json

```jsonc
{
  "jahr": 2025,                              // Pflicht: daraus folgen die Schlüssel der Jahresgrenzen
  "quelle": "Abrechnungen/2025/Konto",       // Ordner der PDFs
  "eigentuemergemeinschaft": "WEG …",
  "bank": "…",
  "konten": [
    {
      "kontonummer": "…",
      "iban": "…", "bic": "…",
      "typ": "Girokonto | Rücklagenkonto …",
      "waehrung": "EUR",
      "saldo_31_12_2024": 1550.67,           // Pflicht: Start der Saldo-Kette (31.12. des Vorjahres)
      "saldo_31_12_2025": 2144.59,           // Pflicht: Ende der Saldo-Kette (31.12. des Jahres)
      "auszuege": [
        {
          "nr": "1/2025",
          "datei": "<PDF-Dateiname>",        // null = Auszug fehlt (Platzhalter)
          "erstellt_am": "2025-01-31",
          "alter_kontostand": { "vom": "2024-12-30", "betrag": 1550.67, "haben": true },
          "neuer_kontostand": { "vom": "2025-01-31", "betrag": 1955.85, "haben": true },
          "transaktionen": [
            {
              "buchungstag": "2025-01-02",
              "wertstellung": "2025-01-02",
              "art": "Dauerauftrag | SEPA-Basis-Lastschrift | SEPA-EU-Überweisung | Lastschrifteinreichung |
                      Überweisungsgutschrift | Retoure (Rücklastschrift) | Entgelt/Auslagen | Abschluss …",
              "partner": "<Empfänger oder Zahlungspflichtiger>",
              "verwendungszweck": "<Originaltext gekürzt, mit Rückverweis auf den Beleg, wenn klar>",
              "betrag": 320.00,
              "soll_haben": "haben | soll"   // haben = Gutschrift, soll = Belastung
            }
          ]
        }
      ]
    }
  ]
}
```

**Platzhalter:** Fehlt ein Auszug, steht er trotzdem als Element mit `"datei": null` und einer `anmerkung` in der
Liste. Sein `neuer_kontostand` kommt aus dem `alter_kontostand` des folgenden Auszugs. Die Prüfung summiert den
Platzhalter nicht und reicht nur den Saldo weiter.

## belege_JJJJ.json

```jsonc
{
  "jahr": 2025,
  "quelle": "Abrechnungen/2025/Belege",
  "verwalter": "…",
  "belege": [
    {
      "datei": "<Dateiname>",
      "typ": "Rechnung | Buchungsliste | Gebührenbescheid | Jahresabrechnung … | Scan (per Bildauswertung erfasst)",
      "absender": "…", "rechnungsnummer": "…", "kundennummer": "…",
      "datum": "JJJJ-MM-TT",
      "objekt": "<Anschrift>",

      // Variante A – Rechnung mit Positionen:
      "positionen": [
        { "pos": "001", "menge": "1 pauschal", "bezeichnung": "…", "einheitspreis": 250.00, "gesamt": 250.00 }
        // oder nur { "bezeichnung": "…", "netto": 59.00 }
      ],
      "nettobetrag": 516.84,
      "mwst_19_prozent": 98.20,              // Schlüssel-Format mwst_<satz>_prozent
      "bruttobetrag": 615.04,

      // Variante B – Buchungsliste der Verwaltung:
      "buchungen": [
        { "b_nr": "17", "datum": "2025-03-31", "kommentar": "Zinsertrag", "betrag": 5.39 }
      ],
      "kontostand_31_12_2024": 3531.50,      // Pflicht in Variante B: Stand 31.12. des Vorjahres
      "gesamtsaldo": -2990.62,               // Summe aller Buchungen
      "kontostand_31_12_2025": 540.88,       // Pflicht in Variante B: Stand 31.12. des Jahres

      // Variante C – ohne Geldbeträge (Bescheide, Anschreiben):
      "betrag": null,
      "anmerkung": "<Kurzbeschreibung, keine Zahlung zu erwarten>"
    }
  ],
  "pruefungen": [                            // Zahl-Zuordnungen zur Kontrolle, auf oberster Ebene
    { "name": "Zahlungen an Firma X == Rechnung", "soll": 3553.28, "ist": 3553.28 }
  ],
  "dubletten_pruefelder": [                  // nur Dokumentation, das Skript prüft per MD5
    { "dateien": ["a.pdf", "b.pdf"], "art": "Vollständiges Duplikat", "erklaerung": "…" }
  ],
  "offene_punkte": [
    "fehlt: Kontoauszug 11/2025 …",
    "Differenz Versicherung 524,47 vs. 527,47 …"
  ]
}
```

## weg_abrechnung_JJJJ_weN.json

Eckdaten der Einzelabrechnung einer Einheit `N`: Gemeinschaft, Zeitraum, Einheit, Ergebnis, Zahlungen, Vorjahre,
Kostenpositionen, Rücklage, Prüfsummen. Das Schema steht in [weg_abrechnung.schema.json](weg_abrechnung.schema.json).
`korrelation_zahlungen.py` liest daraus `einheit.eigentuemer`, `einheit.nummer`, `abrechnungszeitraum` und
`zahlungen.liste` (je Zahlung `datum`, `betrag`, `bewirtschaftung`, `ruecklage`).

## Namenskonventionen, auf die sich die Skripte verlassen

| Feld | Bedeutung |
|------|-----------|
| `jahr` | Abrechnungsjahr. Daraus leitet das Skript die Schlüssel der Jahresgrenzen ab. |
| `saldo_31_12_<Vorjahr>` / `saldo_31_12_<Jahr>` | Anfang und Ende der Saldo-Kette je Konto |
| `kontostand_31_12_<Vorjahr>` / `kontostand_31_12_<Jahr>` | Anfangs- und Endstand einer Buchungsliste |
| `alter_kontostand` / `neuer_kontostand` | Stand je Auszug, mit `betrag` |
| `soll_haben` | `"haben"` = Gutschrift, `"soll"` = Belastung |
| `mwst_<n>_prozent` | MwSt-Satz im Schlüssel (7 oder 19) |
| `positionen[].gesamt` oder `positionen[].netto` | Positionssumme, `gesamt` hat Vorrang |
| `pruefungen[].soll` / `.ist` | freie Zahl-Zuordnungen auf oberster Ebene von `belege_JJJJ.json` |
| `fundstelle` | Herkunft eines Werts, siehe oben |
