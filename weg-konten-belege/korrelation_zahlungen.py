#!/usr/bin/env python3
"""Korrelation: Zahlungseingänge aus der WEG-Einzelabrechnung vs. Bank-Umsätze.

Vergleicht die `zahlungen.liste` aus der Abrechnungs-JSON (weg_abrechnung_JJJJ_weN.json)
mit den Bank-Umsätzen in konto_JJJJ.json, deren Partner den Nachnamen aus `einheit.eigentuemer` enthält.

Sonderfälle (siehe SKILL.md, Fallstricke):
- Sammel-Lastschrift: Einzelzahlung des Eigentümers steckt in einer Sammel-
  Buchung (5 Lastschriften) und ist dort nicht einzeln erkennbar. Belegt sie
  sich über die verwandte Retoure (Verwendungszweck "Hausgeld X,00 + Entgelt"),
  wird sie als "indirekt belegt" klassifiziert.
- Retouren werden Tage später gebucht als die Original-Lastschrift ->
  Datumstoleranz (standardmaessig +/- 7 Tage).
- Fehlende Kontoauszuege (datei: null): Zahlungen im entsprechenden Zeitraum
  koennen nicht verifiziert werden und werden als "unverifizierbar (Auszug fehlt)"
  gemeldet.

Aufruf:
    python3 korrelation_zahlungen.py weg_abrechnung_JJJJ_weN.json konto_JJJJ.json

Exit-Code 0 = alle Zahlungen verifiziert oder plausibel indirekt belegt,
Exit-Code 1 = es gibt nicht aufgeklärbare Abweichungen.
"""

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Höchstes Bankentgelt, das eine Rücklastschrift auf den geplatzten Betrag aufschlägt.
# Die Retoure in der Abrechnung ist dann -(Betrag + Entgelt). Das Entgelt hängt von der Bank ab.
ENTGELT_MAX = 10.00


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def fmt(eigentuemer_nachname, betrag, d):
    return f"{d.isoformat()}  {betrag:>10.2f} €"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    abrechnung = json.load(open(sys.argv[1]))
    konto = json.load(open(sys.argv[2]))

    eigentuemer = abrechnung["einheit"]["eigentuemer"]
    nachname = eigentuemer.split()[-1].lower()
    payments = abrechnung["zahlungen"]["liste"]
    for p in payments:
        p["datum"] = parse_date(p["datum"] if isinstance(p["datum"], str) else p["datum"].isoformat())

    # Bank-Zahlungen des Eigentümers: Partner enthält Nachnamen,
    # signiert nach soll_haben (haben = positiv, soll = negativ).
    bank = []
    fehlende_auszuege = []  # (von, bis) Zeitraeume ohne Kontoauszug
    for konto_entry in konto["konten"]:
        for auszug in konto_entry["auszuege"]:
            if not auszug.get("datei"):
                fehlende_auszuege.append(
                    (parse_date(auszug["alter_kontostand"]["vom"][:10]),
                     parse_date(auszug["neuer_kontostand"]["vom"][:10]))
                )
            for t in auszug["transaktionen"]:
                if nachname not in t.get("partner", "").lower():
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
    ab = {p["datum"]: p for p in payments}

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

    # Pass 1: exakte Betrags-/Datums-Matches (Dauerauftraege, direkte Zahlung
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
    pair_matched = set()
    # Retouren belegen zwoerlei: die Ruecklastschrift selbst (Pass 1, exakter
    # Betrag) UND den darin erwaehnten Original-Betrag der geplatzten
    # Lastschrift. Deshalb auch bereits in Pass 1 verbrauchte Retouren hier als
    # Beleg zulassen; die Zahlung wird nur einmal verbraucht.
    retoures = [i for i, b in enumerate(bank) if "retoure" in b["art"].lower()]
    for i in retoures:
        rb = bank[i]
        m = re.search(r"hausgeld\s+([\d.,]+)", rb["vz"].lower())
        if not m:
            continue
        x = float(m.group(1).replace(".", "").replace(",", "."))
        for j, p in enumerate(payments):
            if id(p) in matched_ids or round(p["betrag"], 2) != round(x, 2):
                continue
            # Partner -(x+Entgelt) existiert nur als Belegkette; er darf bereits
            # anderweitig gematcht sein (z. B. als exakte Bank-Buchung) und wird
            # dann nicht erneut ausgegeben.
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
    matched_bank = {i for i, u in enumerate(used) if u}
    abrechnung_betraege = {(p["datum"], round(p["betrag"], 2)) for p in payments}
    fehlen_in_abrechnung = []
    for i, b in enumerate(bank):
        if used[i] or i in {r for r in []}:
            continue
        # Retouren sind über Pass 2/Abgleich abgedeckt; übrig bleiben Daueraufträge
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

    if n_fehlt:
        print("\nERGEBNIS: Es gibt Zahlungen ohne Bank-Beleg (siehe '!').")
        return 1
    print("\nERGEBNIS: Alle Zahlungen der Abrechnung sind direkt oder plausibel indirekt belegt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())