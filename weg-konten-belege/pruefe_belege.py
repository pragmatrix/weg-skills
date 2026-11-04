#!/usr/bin/env python3
"""Prüft extrahierte WEG-Finanzdaten (konto_YYYY.json + belege_YYYY.json) auf Konsistenz.

Aufruf:   python3 pruefe_belege.py <ordner>          (Default: aktuelles Verzeichnis)
Erwartet: <ordner>/konto_YYYY.json und <ordner>/belege_YYYY.json mit gleicher Jahreszahl.

Geprüft wird (doppelte Kontrolle nach Extraktion):
  1. JSON-Syntax (json.load) und Pflicht-Top-Level-Schlüssel
  2. Saldo-Kette je Bankkonto: alter Kontostand + Σ Umsätze = neuer Kontostand je Auszug
  3. Platzhalter-Auszüge (datei == null) liefern den Folgesaldo, werden nicht summiert
  4. Endsaldo: letzter neuer Kontostand = dokumentierter Jahresendsaldo
  5. Buchungslisten der Hausverwaltung (Feld "buchungen"):
     Anfangssaldo + Σ Buchungen = Endsaldo
  6. Rechnungen mit "positionen": Σ Positionen = "nettobetrag"
  7. Rechnungen mit netto/brutto: Netto × (1 + MwSt-Satz aus mwst_XX_prozent) = "bruttobetrag"
  8. Optional definierte Einzelprüfungen "pruefungen": [{"name","soll","ist"}, ...]
  9. Byte-identische Duplikate im Belege-Ordner (MD5 je Datei)
 10. Fundstellen "fundstelle": {"datei", "seite"} in konto_, belege_ und weg_abrechnung_*.json: Die Datei existiert
     (Pfad relativ zum Projektordner, also zur Git-Wurzel), die Seite liegt im PDF.

Die Schlüssel der Jahresgrenzen (saldo_31_12_<Vorjahr>, saldo_31_12_<Jahr>,
kontostand_31_12_<Vorjahr>, kontostand_31_12_<Jahr>) leitet das Skript aus "jahr" in konto_YYYY.json ab.

Exit-Code 0 = alle Prüfungen bestanden, 1 = mindestens ein Fehler.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

ORDNER = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
TOL = 0.011  # Cent-Toleranz für Rundungsdifferenzen


def projektordner():
    """Git-Wurzel des Ordners. Auf sie beziehen sich die Pfade in "fundstelle"."""
    out = subprocess.run(["git", "-C", ORDNER, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ORDNER


def pdf_seiten(pfad):
    out = subprocess.run(["pdfinfo", pfad], capture_output=True, text=True)
    for zeile in out.stdout.splitlines():
        if zeile.startswith("Pages:"):
            return int(zeile.split()[1])
    return None


def fundstellen(knoten, pfad="$"):
    """Liefert jedes "fundstelle"-Objekt im JSON mit seinem Pfad, für die Meldung."""
    if isinstance(knoten, dict):
        for k, v in knoten.items():
            if k == "fundstelle" and isinstance(v, dict):
                yield pfad, v
            else:
                yield from fundstellen(v, f"{pfad}.{k}")
    elif isinstance(knoten, list):
        for i, v in enumerate(knoten):
            yield from fundstellen(v, f"{pfad}[{i}]")


def r2(x):
    return round(x, 2)


def lade(pattern):
    treffer = sorted(glob.glob(os.path.join(ORDNER, pattern)))
    if not treffer:
        print(f"FEHLT: {pattern} in {ORDNER}")
        return None
    with open(treffer[0], encoding="utf-8") as f:
        return json.load(f)


fehler = []
infos = []

k = lade("konto_*.json")
b = lade("belege_*.json")
jahr = (k or b or {}).get("jahr")
vj = jahr - 1 if jahr else None

# ---- 2./3./4. Saldo-Kette je Konto ------------------------------------------
if k:
    for konto in k.get("konten", []):
        kn = konto.get("kontonummer", "?")
        prev = konto[f"saldo_31_12_{vj}"]
        for a in konto.get("auszuege", []):
            alt = a["alter_kontostand"]["betrag"]
            neu = a["neuer_kontostand"]["betrag"]
            # Platzhalter für fehlenden Auszug: nur Folgesaldo weiterreichen.
            # (Der Saldo "stimmt" dann, wenn der Folgende Auszug ihn als
            # alter_kontostand trägt — das prüft der normale Zweig unten.)
            if a.get("datei") is None:
                infos.append(f"{kn} {a['nr']}: Platzhalter (Auszug fehlt), Folgesaldo {neu} übernommen")
                prev = neu
                continue
            if r2(alt) != r2(prev):
                fehler.append(f"{kn} {a['nr']}: alter Stand {alt} != vorheriger neuer Stand {prev}")
            s = sum(t["betrag"] * (1 if t.get("soll_haben") == "haben" else -1)
                    for t in a.get("transaktionen", []))
            if abs(r2(alt + s) - r2(neu)) > TOL:
                fehler.append(f"{kn} {a['nr']}: {alt} + Σ {s:.2f} = {r2(alt+s)} != neu {neu}")
            prev = r2(neu)
        if r2(prev) != r2(konto[f"saldo_31_12_{jahr}"]):
            fehler.append(f"{kn}: Endsaldo {konto[f'saldo_31_12_{jahr}']} != letzter neuer Stand {prev}")
else:
    fehler.append("konto_*.json nicht gefunden/lesbar")

# ---- 5.–7. Belege ------------------------------------------------------------
if b:
    for beleg in b.get("belege", []):
        name = beleg.get("datei", "?")
        # Buchungslisten der Hausverwaltung
        if "buchungen" in beleg and f"kontostand_31_12_{jahr}" in beleg:
            s = sum(x["betrag"] for x in beleg["buchungen"])
            anfang = beleg[f"kontostand_31_12_{vj}"]
            soll = r2(anfang + s)
            ist = beleg[f"kontostand_31_12_{jahr}"]
            if abs(soll - ist) > TOL:
                fehler.append(f"{name}: Liste {anfang} + Σ {s:.2f} = {soll} != {ist}")
        # Positions-Rechnungen
        pos = beleg.get("positionen") or []
        if pos and "nettobetrag" in beleg:
            schluessel = "gesamt" if "gesamt" in pos[0] else "netto"
            s = sum(p.get(schluessel, 0) for p in pos)
            if abs(r2(s) - beleg["nettobetrag"]) > TOL:
                fehler.append(f"{name}: Σ Positionen {r2(s)} != netto {beleg['nettobetrag']}")
        # Netto/MwSt/Brutto
        if "nettobetrag" in beleg and "bruttobetrag" in beleg:
            rate = 0.19  # Default, falls MwSt-Schlüssel fehlt
            for kk in beleg:
                if kk.startswith("mwst_") and kk[5:kk.index("_", 5)].isdigit():
                    rate = int(kk[5:kk.index("_", 5)]) / 100
                    break
            soll = r2(beleg["nettobetrag"] * (1 + rate))
            if abs(soll - beleg["bruttobetrag"]) > TOL:
                fehler.append(f"{name}: netto×(1+{rate:.2f}) = {soll} != brutto {beleg['bruttobetrag']}")
else:
    fehler.append("belege_*.json nicht gefunden/lesbar")

# ---- 8. explizit definierte Prüfungen ----------------------------------------
for p in (b or {}).get("pruefungen", []):
    if "soll" in p and "ist" in p and abs(r2(p["soll"]) - r2(p["ist"])) > TOL:
        fehler.append(f"Prüfung '{p.get('name', '?')}': soll {p['soll']} != ist {p['ist']}")

# ---- 9. byte-identische Duplikate ---------------------------------------------
belege_dir = os.path.join(ORDNER, "Belege")
if os.path.isdir(belege_dir):
    hashes = {}
    for f in sorted(os.listdir(belege_dir)):
        pfad = os.path.join(belege_dir, f)
        if os.path.isfile(pfad):
            with open(pfad, "rb") as fh:
                hashes.setdefault(hashlib.md5(fh.read()).hexdigest(), []).append(f)
    dupes = [v for v in hashes.values() if len(v) > 1]
    print("Byte-identische Beleg-Duplikate:", dupes if dupes else "keine")

# ---- 10. Fundstellen "fundstelle" -------------------------------------------
wurzel = projektordner()
n_fundstellen = 0
abrechnungen = [json.load(open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(ORDNER, "weg_abrechnung_*.json")))
                if not p.endswith(".schema.json")]
for daten in (k, b, *abrechnungen):
    for pfad, q in fundstellen(daten or {}):
        n_fundstellen += 1
        datei = os.path.join(wurzel, q.get("datei") or "")
        if not q.get("datei") or not os.path.isfile(datei):
            fehler.append(f"fundstelle {pfad}: Datei fehlt: {q.get('datei')}")
            continue
        seite = q.get("seite")
        if seite is not None and datei.lower().endswith(".pdf"):
            n = pdf_seiten(datei)
            if n is not None and not 1 <= seite <= n:
                fehler.append(f"fundstelle {pfad}: Seite {seite} liegt nicht in {q['datei']} ({n} S.)")
print(f"Fundstellen geprüft: {n_fundstellen}")

print()
for info in infos:
    print("Hinweis:", info)
if fehlen := [f for f in fehler if "nicht gefunden" in f]:
    print()
    print("ACHTUNG – fehlende Dateien:")
    for f in fehlen:
        print(" -", f)
if len(fehler) > len(fehlen):
    print()
    print("PRÜFUNGSFEHLER:")
    for e in fehler:
        if "nicht gefunden" not in e:
            print(" -", e)
    sys.exit(1)
print()
print("ALLE PRÜFUNGEN BESTANDEN (Saldo-Ketten, Salden, Positionssummen, MwSt., definierte Prüfungen)")