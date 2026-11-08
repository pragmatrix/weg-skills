#!/usr/bin/env python3
"""Korrelation: Zahlungseingänge aus der WEG-Einzelabrechnung vs. Bank-Umsätze.

Vergleicht die `zahlungen.liste` aus der Abrechnungs-JSON (weg_abrechnung_JJJJ_weN.json)
mit den Bank-Umsätzen in konto_JJJJ.json, deren Partner den vollen Namen eines der Eigentümer aus
`einheit.eigentuemer` trägt (siehe `eigentuemer_namen` und `passt`).

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

Jede Zahlung ohne Bankbuchung (FEHLT) und jede Zahlung im Zeitraum eines fehlenden Auszugs (UNVERIFIZIERBAR) ist
eine Lücke. Eine Lücke ist auch jeder Eingang des Eigentümers im Abrechnungszeitraum, der weder einer Zahlung dieser
Abrechnung noch dem Zahlungseingang auf die Vorjahre zugeordnet ist. Dabei zählen auch die Zahlungen der anderen
Einheiten desselben Eigentümers. Als solche gilt jede Abrechnungs-JSON im selben Ordner mit gleichem Zeitraum und
gleichem Eigentümer. Nennt keine Bankbuchung einen der Eigentümer, ist das eine eigene Lücke, damit eine
abweichende Schreibweise nicht als Reihe einzelner Zahlungslücken durchgeht.

Eine Lücke gilt als geklärt, wenn ein Eintrag unter `offene_punkte` der Abrechnungs-JSON mit ihrem Schlüssel beginnt
(siehe luecken.py). Das Skript gibt die Schlüssel der ungeklärten Lücken aus.

Exit-Code 0 = jede Zahlung ist direkt oder indirekt belegt, oder ihre Lücke ist dokumentiert.
Exit-Code 1 = es gibt mindestens eine Lücke ohne Eintrag unter `offene_punkte`.
"""

import json
import re
import sys
import unicodedata

import luecken
from datetime import datetime
from pathlib import Path

# Höchstes Bankentgelt, das eine Rücklastschrift auf den geplatzten Betrag aufschlägt.
# Die Retoure in der Abrechnung ist dann -(Betrag + Entgelt). Das Entgelt hängt von der Bank ab.
ENTGELT_MAX = 10.00


UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Wörter im Feld `einheit.eigentuemer`, die zu keinem Namen gehören.
FUELLWOERTER = {"eheleute", "familie", "herr", "herrn", "frau"}
# Trennt Personen innerhalb eines Teils von `einheit.eigentuemer`, etwa „Hans und Erika Müller“.
PERSONEN_TRENNER = re.compile(r"\s+und\s+|&", re.IGNORECASE)


def woerter(text):
    """Die Wörter eines Namens in einer Form, in der Schreibweisen der Bank und der Abrechnung gleich aussehen.

    Groß- und Kleinschreibung, Umlaute („Müller“ und „MUELLER“), andere Akzente („René“ und „RENE“) und Satzzeichen
    spielen dann keine Rolle. Ein Bindestrich bleibt im Wort, damit „Hans-Peter“ ein Vorname bleibt. `teile` trennt
    ihn für den Vergleich. Abkürzungen mit Punkt wie „Dr.“ zählen nicht, weil die Bank sie oft weglässt.
    """
    text = unicodedata.normalize("NFC", text).casefold().translate(UMLAUTE)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    ergebnis = []
    for w in text.split():
        if w.endswith("."):
            continue
        w = re.sub(r"[^a-z0-9-]", "", w).strip("-")
        if w and w not in FUELLWOERTER:
            ergebnis.append(w)
    return ergebnis


def teile(woerter_liste):
    """Die Wörter ohne Bindestriche als Menge. So passt „Hans-Peter“ auf „HANS PETER“ und auf „HANS-PETER“."""
    return {t for w in woerter_liste for t in w.split("-") if t}


def eigentuemer_namen(feld):
    """Die einzelnen Eigentümer aus `einheit.eigentuemer`, je als Menge der Wörter ihres vollen Namens.

    Ein „;“ trennt Eigentümer mit verschiedenen Nachnamen. Innerhalb eines Teils trennen „und“ und „&“ die Personen,
    und alle Personen eines Teils tragen denselben Nachnamen. Steht ein Komma im Teil, ist alles davor dieser
    Nachname, wie in „Müller, Hans und Erika“. Sonst ist es das letzte Wort der letzten Person. Jede Person, die nicht
    schon darauf endet, bekommt ihn angehängt. So wird „Hans Peter und Erika Müller“ zu „Hans Peter Müller“ und
    „Erika Müller“, und eine Zahlung von „Hans Peter Schmidt“ zählt nicht.
    """
    namen = []
    for teil in feld.split(";"):
        nachname = []
        if "," in teil:
            vorne, teil = teil.split(",", 1)
            nachname = woerter(vorne)
        personen = [p for p in (woerter(x) for x in PERSONEN_TRENNER.split(teil)) if p]
        if not nachname:
            nachname = personen[-1][-1:] if personen and len(personen[-1]) > 1 else []
            personen = [p if p[-len(nachname):] == nachname else p + nachname for p in personen]
        else:
            personen = [p + nachname for p in personen] or [nachname]
        namen += [teile(p) for p in personen if p]
    return namen


def passt(namen, partner):
    """Nennt der Partner einer Bankbuchung alle Wörter des Namens von mindestens einem der Eigentümer?"""
    partner_teile = teile(woerter(partner))
    return any(name <= partner_teile for name in namen)


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    abrechnung = json.load(open(sys.argv[1]))
    konto = json.load(open(sys.argv[2]))

    eigentuemer = abrechnung["einheit"]["eigentuemer"]
    namen = eigentuemer_namen(eigentuemer)
    zeitraum = abrechnung["abrechnungszeitraum"]
    von, bis = parse_date(zeitraum["von"]), parse_date(zeitraum["bis"])
    payments = abrechnung["zahlungen"]["liste"]
    for p in payments:
        p["datum"] = parse_date(p["datum"])

    # Die Abrechnungen der anderen Einheiten desselben Eigentümers im selben Zeitraum. Ihre Zahlungen und ihr
    # Zahlungseingang auf die Vorjahre sind keine Lücke dieser Abrechnung. Die Reihenfolge der Eigentümer im Feld
    # zählt nicht. Zwei Dateien für dieselbe Einheit, etwa eine Kopie, würden Eingänge doppelt verbrauchen.
    eigene = Path(sys.argv[1]).resolve()
    eigentuemer_menge = {frozenset(n) for n in namen}
    einheiten = {abrechnung["einheit"]["nummer"]: eigene}
    andere = []
    for pfad in sorted(eigene.parent.glob("weg_abrechnung_*_we*.json")):
        if pfad.resolve() == eigene:
            continue
        a = json.load(open(pfad, encoding="utf-8"))
        if a.get("abrechnungszeitraum") != zeitraum:
            continue
        nummer = a["einheit"]["nummer"]
        if nummer in einheiten:
            sys.exit(f"ABBRUCH: {einheiten[nummer].name} und {pfad.name} gelten beide für Einheit {nummer} "
                     f"im selben Zeitraum. Eine davon gehört nicht in den Ordner.")
        einheiten[nummer] = pfad
        if {frozenset(n) for n in eigentuemer_namen(a["einheit"]["eigentuemer"])} == eigentuemer_menge:
            andere.append(a)
    andere_zahlungen = [dict(q, datum=parse_date(q["datum"])) for a in andere for q in a["zahlungen"]["liste"]]
    vorjahres_eingaenge = [a.get("vorjahre", {}).get("zahlungseingang", 0) for a in (abrechnung, *andere)]

    # Bank-Zahlungen des Eigentümers. Ihr Partner enthält jedes Wort des Namens eines Eigentümers. Der Betrag trägt
    # das Vorzeichen aus soll_haben (haben positiv, soll negativ).
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
                if not passt(namen, t.get("partner", "")):
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

    # Pass 3: Bank-Eingänge, die zu einer anderen Einheit desselben Eigentümers oder zum Zahlungseingang auf die
    # Vorjahre gehören. Erst danach, damit die Zahlungen dieser Abrechnung zuerst zugeordnet werden.
    for q in andere_zahlungen:
        m = find(same, q, 3)
        if m is not None:
            used[m[1]] = True
    for eingang in vorjahres_eingaenge:
        if eingang > 0:
            i = next((i for i, b in enumerate(bank)
                      if not used[i] and von <= b["datum"] <= bis and round(b["betrag"], 2) == round(eingang, 2)),
                     None)
            if i is not None:
                used[i] = True

    # Pass 4: Rest klassifizieren.
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

    # Kontrolle: Zahlungseingänge des Eigentümers im Abrechnungszeitraum, die keiner Zahlung zugeordnet sind.
    fehlen_in_abrechnung = []
    for i, b in enumerate(bank):
        if used[i] or not von <= b["datum"] <= bis:
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

    if not bank:
        print(f"\nKeine Bankbuchung nennt einen der Eigentümer aus „{eigentuemer}“. "
              "Schreibweise im Kontoauszug prüfen.")
    if fehlen_in_abrechnung:
        print("\nZahlungseingänge des Eigentümers in der Bank, die nicht in der Abrechnung stehen:")
        for b in fehlen_in_abrechnung:
            print(f"  ? {b['datum']}  {b['betrag']:>10.2f} €  Auszug {b['auszug']}  VZ: {b['vz']}")

    lueckenliste = [luecken.zahlung(status.lower(), p["datum"], p["betrag"])
                    for p, status, _ in results if status in ("FEHLT", "UNVERIFIZIERBAR")]
    lueckenliste += [luecken.zahlung("fehlt in Abrechnung", b["datum"], b["betrag"]) for b in fehlen_in_abrechnung]
    if not bank:
        lueckenliste.append(luecken.bankbuchung(eigentuemer))
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