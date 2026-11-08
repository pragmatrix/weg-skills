#!/usr/bin/env python3
"""Prüft extrahierte WEG-Finanzdaten (konto_YYYY.json + belege_YYYY.json) auf Konsistenz.

Aufruf:   python3 pruefe_belege.py <ordner>          (Default: aktuelles Verzeichnis)
Erwartet: <ordner>/konto_YYYY.json und <ordner>/belege_YYYY.json mit gleicher Jahreszahl. Fehlt eine der beiden
Dateien, passen mehrere auf das Muster oder weichen die Jahre ab, ist das ein Fehler.

Geprüft wird (doppelte Kontrolle nach Extraktion):
  1. JSON-Syntax (json.load) und Pflicht-Top-Level-Schlüssel
  2. Saldo-Kette je Bankkonto: alter Kontostand + Σ Umsätze = neuer Kontostand je Auszug
  3. Platzhalter-Auszüge (datei == null) liefern den Folgesaldo und werden nicht summiert. Jeder ist eine Lücke, die
     ein Eintrag unter "offene_punkte" in belege_YYYY.json dokumentieren muss (siehe luecken.py).
  4. Endsaldo: letzter neuer Kontostand = dokumentierter Jahresendsaldo
  5. Buchungslisten der Hausverwaltung (Feld "buchungen"):
     Anfangssaldo + Σ Buchungen = Endsaldo, und Σ Buchungen = "gesamtsaldo", wenn das Feld existiert
  6. Rechnungen mit "positionen": Σ Positionen = "nettobetrag"
  7. Rechnungen mit netto/brutto: Netto + Σ mwst_<n>_prozent = "bruttobetrag". Ohne MwSt-Schlüssel gilt 0 %.
     Bei nur einem Satz muss der MwSt-Betrag außerdem auf einen Cent genau Netto × Satz sein.
  8. Optional definierte Einzelprüfungen "pruefungen": [{"name","soll","ist"}, ...]
  9. Byte-identische Duplikate im Belege-Ordner (MD5 je Datei). Eine Gruppe gilt als geklärt, wenn ein Eintrag
     unter "dubletten_pruefelder" alle ihre Dateien nennt.
 10. Fundstellen "fundstelle": {"datei", "seite"} in konto_, belege_ und weg_abrechnung_*.json: Die Datei existiert
     (Pfad relativ zum Projektordner, also zur Git-Wurzel), die Seite liegt im PDF.

Die Schlüssel der Jahresgrenzen (saldo_31_12_<Vorjahr>, saldo_31_12_<Jahr>,
kontostand_31_12_<Vorjahr>, kontostand_31_12_<Jahr>) leitet das Skript aus "jahr" in konto_YYYY.json ab.

Alle Beträge werden als Dezimalzahl gelesen und exakt verglichen. Eine Toleranz gibt es nur für Netto × Satz.

Exit-Code 0 = alle Prüfungen bestanden, 1 = mindestens ein Fehler.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

# Den Projektordner bestimmt der Skill weg-eigentuemer-ablage. Auf ihn beziehen sich die Pfade in "fundstelle".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "weg-eigentuemer-ablage" / "scripts"))
from projekt import projektordner  # noqa: E402

import luecken  # noqa: E402

ORDNER = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
CENT = Decimal("0.01")
# Der MwSt-Betrag einer Rechnung darf um einen Cent von Netto × Satz abweichen, weil Rechnungen je Position runden.
MWST_TOLERANZ = CENT
MWST_SCHLUESSEL = re.compile(r"mwst_(\d+)_prozent")


def pdf_seiten(pfad):
    """Seitenzahl des PDFs laut `pdfinfo`, oder None, wenn `pdfinfo` sie nicht liefert."""
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


def lade_json(pfad):
    """Liest eine JSON-Datei. Kommazahlen werden zu Decimal, damit Summen exakt bleiben."""
    with open(pfad, encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


fehler = []
infos = []


def lade(pattern):
    """Liest die eine Datei, die auf `pattern` passt. Keine oder mehrere Treffer sind ein Fehler."""
    treffer = sorted(glob.glob(os.path.join(ORDNER, pattern)))
    if len(treffer) != 1:
        namen = ", ".join(os.path.basename(t) for t in treffer) or "keine"
        fehler.append(f"genau eine Datei {pattern} in {ORDNER} erwartet, gefunden: {namen}")
        return None, None
    return lade_json(treffer[0]), treffer[0]


k, k_pfad = lade("konto_*.json")
b, b_pfad = lade("belege_*.json")
jahr = None
for daten, pfad in ((k, k_pfad), (b, b_pfad)):
    if daten is None:
        continue
    name = os.path.basename(pfad)
    if not isinstance(daten.get("jahr"), int):
        fehler.append(f"{name}: Feld \"jahr\" fehlt oder ist keine Jahreszahl")
        continue
    if f"_{daten['jahr']}." not in name:
        fehler.append(f"{name}: Jahr im Dateinamen passt nicht zu \"jahr\": {daten['jahr']}")
    if jahr is None:
        jahr = daten["jahr"]
    elif daten["jahr"] != jahr:
        fehler.append(f"Jahre weichen ab: konto {jahr}, belege {daten['jahr']}")
vj = jahr - 1 if jahr else None

# ---- 2./3./4. Saldo-Kette je Konto ------------------------------------------
if k and jahr:
    for konto in k.get("konten", []):
        kn = konto.get("kontonummer", "?")
        prev = konto[f"saldo_31_12_{vj}"]
        for a in konto.get("auszuege", []):
            alt = a["alter_kontostand"]["betrag"]
            neu = a["neuer_kontostand"]["betrag"]
            # Ein Platzhalter steht für einen fehlenden Auszug und reicht nur seinen neuen Stand weiter.
            # Ob dieser Stand stimmt, prüft der nächste Auszug, dessen alter Stand ihm gleichen muss.
            if a.get("datei") is None:
                luecke = luecken.kontoauszug(kn, a["nr"])
                if luecken.dokumentiert(luecke, (b or {}).get("offene_punkte")):
                    infos.append(f"{luecke} (Platzhalter, dokumentiert), Folgesaldo {neu} übernommen")
                else:
                    fehler.append(f"Lücke ohne Eintrag unter offene_punkte in belege_{jahr}.json: {luecke}")
                prev = neu
                continue
            if alt != prev:
                fehler.append(f"{kn} {a['nr']}: alter Stand {alt} != vorheriger neuer Stand {prev}")
            s = sum((t["betrag"] * (1 if t.get("soll_haben") == "haben" else -1)
                     for t in a.get("transaktionen", [])), Decimal(0))
            if alt + s != neu:
                fehler.append(f"{kn} {a['nr']}: {alt} + Σ {s:.2f} = {alt + s} != neu {neu}")
            prev = neu
        if prev != konto[f"saldo_31_12_{jahr}"]:
            fehler.append(f"{kn}: Endsaldo {konto[f'saldo_31_12_{jahr}']} != letzter neuer Stand {prev}")

# ---- 5.–7. Belege ------------------------------------------------------------
if b and jahr:
    for beleg in b.get("belege", []):
        name = beleg.get("datei", "?")
        # Buchungslisten der Hausverwaltung
        if "buchungen" in beleg:
            fehlende = [f"kontostand_31_12_{j}" for j in (vj, jahr) if f"kontostand_31_12_{j}" not in beleg]
            s = sum((x["betrag"] for x in beleg["buchungen"]), Decimal(0))
            if fehlende:
                fehler.append(f"{name}: Buchungsliste ohne {', '.join(fehlende)}")
            else:
                anfang = beleg[f"kontostand_31_12_{vj}"]
                ist = beleg[f"kontostand_31_12_{jahr}"]
                if anfang + s != ist:
                    fehler.append(f"{name}: Liste {anfang} + Σ {s:.2f} = {anfang + s} != {ist}")
            if "gesamtsaldo" in beleg and s != beleg["gesamtsaldo"]:
                fehler.append(f"{name}: Σ Buchungen {s:.2f} != gesamtsaldo {beleg['gesamtsaldo']}")
        # Positions-Rechnungen
        pos = beleg.get("positionen") or []
        if pos and "nettobetrag" in beleg:
            schluessel = "gesamt" if "gesamt" in pos[0] else "netto"
            s = sum((p.get(schluessel, 0) for p in pos), Decimal(0))
            if s != beleg["nettobetrag"]:
                fehler.append(f"{name}: Σ Positionen {s} != netto {beleg['nettobetrag']}")
        # Netto + MwSt. = Brutto. Jeder Schlüssel mwst_<n>_prozent trägt den MwSt-Betrag zum Satz n.
        if "nettobetrag" in beleg and "bruttobetrag" in beleg:
            netto, brutto = beleg["nettobetrag"], beleg["bruttobetrag"]
            mwst = {}
            for kk, betrag in beleg.items():
                if not kk.startswith("mwst_"):
                    continue
                m = MWST_SCHLUESSEL.fullmatch(kk)
                if not m or not isinstance(betrag, (int, Decimal)):
                    fehler.append(f"{name}: {kk} ist kein Betrag im Format mwst_<n>_prozent")
                    continue
                mwst[int(m.group(1))] = betrag
            summe = sum(mwst.values(), Decimal(0))
            if netto + summe != brutto:
                fehler.append(f"{name}: netto {netto} + MwSt. {summe} = {netto + summe} != brutto {brutto}")
            if len(mwst) == 1:
                satz, betrag = next(iter(mwst.items()))
                # json liefert einen Betrag ohne Nachkommastellen als int. Mit dem int-Satz ergäbe das einen float
                # ohne quantize.
                erwartet = (Decimal(netto) * satz / 100).quantize(CENT)
                if abs(erwartet - betrag) > MWST_TOLERANZ:
                    fehler.append(f"{name}: {satz} % von {netto} = {erwartet} != MwSt. {betrag}")

# ---- 8. explizit definierte Prüfungen ----------------------------------------
for p in (b or {}).get("pruefungen", []):
    if "soll" in p and "ist" in p and p["soll"] != p["ist"]:
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
    geklaert = [set(map(os.path.basename, d.get("dateien", []))) for d in (b or {}).get("dubletten_pruefelder", [])]
    for gruppe in (v for v in hashes.values() if len(v) > 1):
        if any(set(gruppe) <= g for g in geklaert):
            infos.append(f"byte-identische Belege, geklärt unter dubletten_pruefelder: {', '.join(gruppe)}")
        else:
            fehler.append(f"byte-identische Belege ohne Eintrag unter dubletten_pruefelder: {', '.join(gruppe)}")

# ---- 10. Fundstellen "fundstelle" -------------------------------------------
# Ohne Projektordner oder pdfinfo ist Prüfung 10 nicht möglich. Das ist ein Fehler wie jeder andere, damit die
# Befunde der Prüfungen 1 bis 9 trotzdem erscheinen.
try:
    wurzel = str(projektordner(ORDNER))
except SystemExit as abbruch:
    fehler.append(f"Fundstellen nicht geprüft: {abbruch}")
    wurzel = None
hat_pdfinfo = shutil.which("pdfinfo") is not None
if wurzel and not hat_pdfinfo:
    fehler.append("Seiten der Fundstellen nicht geprüft: pdfinfo fehlt. Es gehört zu Poppler.")
n_fundstellen = 0
abrechnungen = [lade_json(p)
                for p in sorted(glob.glob(os.path.join(ORDNER, "weg_abrechnung_*.json")))
                if not p.endswith(".schema.json")]
for daten in (k, b, *abrechnungen) if wurzel else ():
    for pfad, q in fundstellen(daten or {}):
        n_fundstellen += 1
        datei = os.path.join(wurzel, q.get("datei") or "")
        if not q.get("datei") or not os.path.isfile(datei):
            fehler.append(f"fundstelle {pfad}: Datei fehlt: {q.get('datei')}")
            continue
        seite = q.get("seite")
        if seite is not None and hat_pdfinfo and datei.lower().endswith(".pdf"):
            n = pdf_seiten(datei)
            if n is None:
                fehler.append(f"fundstelle {pfad}: pdfinfo liefert keine Seitenzahl für {q['datei']}")
            elif not 1 <= seite <= n:
                fehler.append(f"fundstelle {pfad}: Seite {seite} liegt nicht in {q['datei']} ({n} S.)")
print(f"Fundstellen geprüft: {n_fundstellen}")

print()
for info in infos:
    print("Hinweis:", info)
if fehler:
    print()
    print("PRÜFUNGSFEHLER:")
    for e in fehler:
        print(" -", e)
    sys.exit(1)
print()
print("ALLE PRÜFUNGEN BESTANDEN (Saldo-Ketten, Salden, Positionssummen, MwSt., definierte Prüfungen, Duplikate)")