#!/usr/bin/env python3
"""Korrelation: Zahlungseingänge aus der WEG-Einzelabrechnung vs. Bank-Umsätze.

Vergleicht die `zahlungen.liste` aus der Abrechnungs-JSON (weg_abrechnung_JJJJ_weN.json)
mit den Bank-Umsätzen in konto_JJJJ.json, deren Partner den vollen Namen aus `einheit.eigentuemer` trägt
(siehe `namens_woerter`).

Sonderfälle (siehe SKILL.md, Fallstricke):
- Sammel-Lastschrift: Die Einzelzahlung des Eigentümers steckt in einer Sammelbuchung
  über die Lastschriften mehrerer Eigentümer und ist dort nicht einzeln erkennbar.
  Belegt sie sich über die verwandte Retoure (Verwendungszweck "Hausgeld X,00 + Entgelt"),
  wird sie als "indirekt belegt" klassifiziert. Sonst bleibt sie FEHLT, und ihre Lücke
  braucht einen Eintrag unter `offene_punkte`.
- Datumstoleranz: Pass 1 ±3 Tage, Retoure ±7 Tage. Eine Retoure wird Tage nach
  der Original-Lastschrift gebucht.
- Fehlende Kontoauszüge (datei: null): Zahlungen im entsprechenden Zeitraum
  können nicht verifiziert werden und werden als "unverifizierbar (Auszug fehlt)"
  gemeldet.

Aufruf:
    python3 korrelation_zahlungen.py weg_abrechnung_JJJJ_weN.json konto_JJJJ.json

Jede Zahlung ohne Bankbuchung (FEHLT), jede Zahlung im Zeitraum eines fehlenden Auszugs (UNVERIFIZIERBAR) und jeder
Eingang des Eigentümers, der in der Abrechnung fehlt, ist eine Lücke. Eine Lücke gilt als geklärt, wenn ein Eintrag
unter `offene_punkte` der Abrechnungs-JSON mit ihrem Schlüssel beginnt (siehe luecken.py). Das Skript gibt die
Schlüssel der ungeklärten Lücken aus.

Exit-Code 0 = jede Zahlung ist direkt oder indirekt belegt, oder ihre Lücke ist dokumentiert.
Exit-Code 1 = es gibt mindestens eine Lücke ohne Eintrag unter `offene_punkte`.
"""

import json
import re
import sys
import unicodedata

import luecken
from datetime import datetime

# Höchstes Bankentgelt, das eine Rücklastschrift auf den geplatzten Betrag aufschlägt.
# Die Retoure in der Abrechnung ist dann -(Betrag + Entgelt). Das Entgelt hängt von der Bank ab.
ENTGELT_MAX = 10.00


UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def namens_woerter(name):
    """Die Wörter eines Namens in einer Form, in der Schreibweisen der Bank und der Abrechnung gleich aussehen.

    Groß- und Kleinschreibung, Umlaute („Müller“ und „MUELLER“), Satzzeichen und die Reihenfolge („Müller, Hans“ und
    „Hans Müller“) spielen dann keine Rolle. Abkürzungen mit Punkt wie „Dr.“ zählen nicht, weil die Bank sie oft
    weglässt.
    """
    name = unicodedata.normalize("NFC", name).casefold().translate(UMLAUTE)
    woerter = [w for w in name.replace(",", " ").split() if not w.endswith(".")]
    return {w for w in (re.sub(r"[^a-z0-9-]", "", w) for w in woerter) if w}


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    abrechnung = json.load(open(sys.argv[1]))
    konto = json.load(open(sys.argv[2]))

    eigentuemer = abrechnung["einheit"]["eigentuemer"]
    name = namens_woerter(eigentuemer)
    payments = abrechnung["zahlungen"]["liste"]
    for p in payments:
        p["datum"] = parse_date(p["datum"])

    # Bank-Zahlungen des Eigentümers: Der Partner enthält jedes Wort seines Namens als ganzes Wort,
    # signiert nach soll_haben (haben = positiv, soll = negativ).
    bank = []
    fehlende_auszuege = []  # (von, bis) Zeiträume ohne Kontoauszug
    for konto_entry in konto["konten"]:
        for auszug in konto_entry["auszuege"]:
            if not auszug.get("datei"):
                fehlende_auszuege.append(
                    (parse_date(auszug["alter_kontostand"]["vom"][:10]),
                     parse_date(auszug["neuer_kontostand"]["vom"][:10]))
                )
            for t in auszug["transaktionen"]:
                if not name <= namens_woerter(t.get("partner", "")):
                    continue
                betrag = t["betrag"] if t.get("soll_haben") == "haben" else -t["betrag"]
                bank.append({
                    "datum": parse_date(t["buchungstag"]),
                    "betrag": round(betrag, 2),
                    "art": t.get("art", ""),
                    "vz": t.get("verwendungszweck", ""),
                    "auszug": auszug["nr"],
                    "konto": konto_entry["kontonummer"],
                    "verbatim": t,
                })

    def in_fehlendem_auszug(d):
        return any(lo <= d <= hi for lo, hi in fehlende_auszuege)

    used = [False] * len(bank)
    results = []  # (payment, status, hinweis)

    def find(match_fn, p, tol_days):
        best = None
        for i, b in enumerate(bank):
            if used[i] or not match_fn(p, b):
                continue
            diff = abs((b["datum"] - p["datum"]).days)
            if diff <= tol_days and (best is None or diff < best[0]):
                best = (diff, i)
        return best

    same = lambda p, b: round(b["betrag"], 2) == round(p["betrag"], 2)

    matched_ids = set()  # bereits belegte Abrechnungs-Zahlungen

    # Pass 1: exakte Betrags-/Datums-Matches (Daueraufträge, direkte Zahlungen).
    for p in payments:
        m = find(same, p, 3)
        if m is not None:
            used[m[1]] = True
            matched_ids.add(id(p))
            results.append((p, "OK", f"Bank {bank[m[1]]['auszug']} (Konto {bank[m[1]]['konto']})"))

    # Pass 2: Lastschrift + Retoure-Paare.
    # Muster: Abrechnung führt eine Zahlung +X (per Lastschrift, in der
    # Sammel-Lastschrift aggregiert) und eine Retoure -(X+Entgelt). In der Bank
    # existiert nur die Retoure, deren Verwendungszweck X erwähnt.
    # Eine Retoure belegt zweierlei: die Rücklastschrift selbst (Pass 1, exakter
    # Betrag) und den darin erwähnten Original-Betrag der geplatzten Lastschrift.
    # Deshalb dient hier auch eine schon in Pass 1 verbrauchte Retoure als Beleg.
    # Jede Zahlung der Abrechnung wird trotzdem nur einmal verbraucht.
    retoures = [i for i, b in enumerate(bank) if "retoure" in b["art"].lower()]
    for i in retoures:
        rb = bank[i]
        m = re.search(r"hausgeld\s+([\d.,]+)", rb["vz"].lower())
        if not m:
            continue
        x = float(m.group(1).replace(".", "").replace(",", "."))
        for p in payments:
            if id(p) in matched_ids or round(p["betrag"], 2) != round(x, 2):
                continue
            # Die Gegenbuchung -(x + Entgelt) in der Abrechnung ist Teil derselben Belegkette.
            # Sie darf schon anderweitig zugeordnet sein, etwa als exakte Bank-Buchung.
            # Dann wird sie nicht noch einmal ausgegeben.
            partner_retoure = next(
                (q for q in payments
                 if 0 < round(-q["betrag"] - x, 2) <= ENTGELT_MAX
                 and abs((q["datum"] - p["datum"]).days) <= 2),
                None)
            if partner_retoure and abs((rb["datum"] - p["datum"]).days) <= 7:
                used[i] = True
                matched_ids.add(id(p))
                if id(partner_retoure) not in matched_ids:
                    matched_ids.add(id(partner_retoure))
                    results.append((partner_retoure, "OK", f"Retoure {rb['auszug']} vom {rb['datum']}"))
                results.append((p, "INDIREKT", f"belegt durch Retoure {rb['auszug']} vom {rb['datum']} (VZ: {rb['vz']})"))
                break

    # Pass 3: Rest klassifizieren.
    verifiziert = 0
    probleme = []
    for p in payments:
        if id(p) in matched_ids:
            continue
        if in_fehlendem_auszug(p["datum"]):
            results.append((p, "UNVERIFIZIERBAR", "Kontoauszug fehlt für diesen Zeitraum"))
            probleme.append(p)
        else:
            results.append((p, "FEHLT", "keine passende Bank-Buchung gefunden"))
            probleme.append(p)

    # Kontrolle: Bank-Buchungen des Eigentümers, die in der Abrechnung fehlen
    # (innerhalb des Abrechnungszeitraums, ohne Abgleich über Sammel-Lastschrift).
    fehlen_in_abrechnung = []
    for i, b in enumerate(bank):
        if used[i]:
            continue
        # Retouren deckt Pass 2 ab. Übrig bleiben Daueraufträge und Überweisungen.
        if "retoure" in b["art"].lower():
            continue
        if b["betrag"] > 0:  # Zahlungseingänge
            fehlen_in_abrechnung.append(b)

    # --- Ausgabe ---
    print(f"Korrelation Zahlungen {abrechnung['abrechnungszeitraum']['von']}..{abrechnung['abrechnungszeitraum']['bis']} - "
          f"{eigentuemer} (Einheit {abrechnung['einheit']['nummer']})")
    print("=" * 100)
    for p, status, hinweis in sorted(results, key=lambda r: (r[0]["datum"], r[0]["betrag"])):
        marker = {"OK": "+", "INDIREKT": "~", "UNVERIFIZIERBAR": "?", "FEHLT": "!"}[status]
        print(f"{marker} {p['datum']}  {p['betrag']:>10.2f} €  [Bew {p['bewirtschaftung']:>8.2f} | Rückl {p['ruecklage']:>7.2f}]  {status:16s} {hinweis}")

    if fehlende_auszuege:
        print("\nFehlende Kontoauszüge (Zahlungen dort nicht prüfbar):")
        for lo, hi in fehlende_auszuege:
            print(f"  {lo} .. {hi}")

    s_ab = round(sum(p["betrag"] for p in payments), 2)
    print(f"\nSumme Zahlungen lt. Abrechnung:  {s_ab:>10.2f} €")
    n_ok = sum(1 for _, s, _ in results if s == "OK")
    n_ind = sum(1 for _, s, _ in results if s == "INDIREKT")
    n_unv = sum(1 for _, s, _ in results if s == "UNVERIFIZIERBAR")
    n_fehlt = sum(1 for _, s, _ in results if s == "FEHLT")
    print(f"  direkt belegt: {n_ok} | indirekt belegt (Retoure): {n_ind} | unverifizierbar (Auszug fehlt): {n_unv} | OHNE Bank-Beleg: {n_fehlt}")

    if fehlen_in_abrechnung:
        print("\nHinweis - Zahlungseingänge des Eigentümers in der Bank, die nicht in der Abrechnung stehen:")
        for b in fehlen_in_abrechnung:
            print(f"  ? {b['datum']}  {b['betrag']:>10.2f} €  Auszug {b['auszug']}  VZ: {b['vz']}")

    lueckenliste = [luecken.zahlung(status.lower(), p["datum"], p["betrag"])
                    for p, status, _ in results if status in ("FEHLT", "UNVERIFIZIERBAR")]
    lueckenliste += [luecken.zahlung("fehlt in Abrechnung", b["datum"], b["betrag"]) for b in fehlen_in_abrechnung]
    offen = [l for l in lueckenliste if not luecken.dokumentiert(l, abrechnung.get("offene_punkte"))]
    if offen:
        print("\nERGEBNIS: Lücken ohne Eintrag unter offene_punkte. Jeder Eintrag beginnt mit dem Schlüssel:")
        for l in offen:
            print(f"  {l}")
        return 1
    print(f"\nERGEBNIS: Jede Zahlung ist belegt, oder ihre Lücke ist dokumentiert ({len(lueckenliste)} Lücken).")
    return 0


if __name__ == "__main__":
    sys.exit(main())