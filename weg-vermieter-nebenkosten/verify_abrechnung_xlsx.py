"""Verifiziert die template-basierte Nebenkostenabrechnung-.xlsx gegen die
JSON-Datenbasis UND gegen das Vorjahres-Template.

Datenprüfung: Jede Position der Datenbasis nennt `betrkv` und ihre Herkunft in
`fundstelle` oder `berechnung`.

Wertprüfungen: alle umlagefähigen Positionen aus dem JSON stehen in der XLSX
(Spalte A) in korrekter Reihenfolge mit korrektem Betrag (Spalte F). Summe,
Vorauszahlung und Ergebnis stimmen mit der Datenbasis überein. Formeln wertet das
Skript selbst aus, weil openpyxl keine berechneten Werte schreibt. Das Ergebnis
heißt „Ihre Nachzahlung“ oder, wenn es negativ ist, „Ihr Guthaben“.

Textprüfungen: Titel und Einleitung nennen das Abrechnungsjahr und nicht mehr das
Vorjahr. Das Datum ist `datum_abrechnung`.

Formatprüfungen (Template-Vergleich): identische verbundene Zellen,
Spaltenbreiten, Zeilenhöhen, Fonts und Zahlenformate fester Ankerzellen.

Verwendung, im Projektordner:
    verify_abrechnung_xlsx.py <jahr> [<template.xlsx>]

Geprüft wird die einzige `*Nebenkostenabrechnung*.xlsx` in `Vermietung/<jahr>/`.
Vorlage wie im build-Skript (nk_pfade.py).

Exit 0 = alle Prüfungen bestanden.
"""

import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string

import nk_pfade
from nk_pfade import r2

TOKEN = re.compile(r'\s*(?:(?P<zahl>\d+(?:\.\d+)?)|(?P<ref>\$?[A-Z]{1,3}\$?\d+)|(?P<op>SUM\(|[-+():,]))',
                   re.IGNORECASE)


def zelle(ref: str) -> tuple[int, int]:
    m = re.fullmatch(r'\$?([A-Z]{1,3})\$?(\d+)', ref, re.IGNORECASE)
    return int(m.group(2)), column_index_from_string(m.group(1).upper())


def wert(ws, r: int, c: int, tiefe: int = 0) -> Decimal:
    """Wert einer Zelle. Eine Formel aus Zellbezügen, Zahlen, +, −, Klammern und SUM wird ausgewertet. Jede
    andere Formel bricht mit ValueError ab, damit keine Formel ungeprüft durchgeht."""
    v = ws.cell(r, c).value
    if v is None:
        return Decimal(0)
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    if not (isinstance(v, str) and v.startswith('=')) or tiefe > 20:
        raise ValueError(f'Zelle ({r},{c}) ist weder Zahl noch prüfbare Formel: {v!r}')
    text, pos, tokens = v[1:], 0, []
    while pos < len(text.rstrip()):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f'Formel in Zelle ({r},{c}) nicht prüfbar: {v!r}')
        tokens.append((m.lastgroup, m.group(m.lastgroup).upper()))
        pos = m.end()
    tokens.append(('ende', ''))
    i = 0

    def nimm(erwartet=None):
        nonlocal i
        art, t = tokens[i]
        if erwartet is not None and t != erwartet:
            raise ValueError(f'Formel in Zelle ({r},{c}) nicht prüfbar: {v!r}')
        i += 1
        return art, t

    def summand() -> Decimal:
        art, t = nimm()
        if t in ('-', '+'):
            x = summand()
            return -x if t == '-' else x
        if t == '(':
            x = ausdruck()
            nimm(')')
            return x
        if art == 'zahl':
            return Decimal(t)
        if art == 'ref':
            if tokens[i][1] == ':':
                raise ValueError(f'Bereich außerhalb von SUM in Zelle ({r},{c}): {v!r}')
            return wert(ws, *zelle(t), tiefe + 1)
        if t == 'SUM(':
            s = Decimal(0)
            while True:
                art2, a = nimm()
                if art2 != 'ref':
                    raise ValueError(f'Formel in Zelle ({r},{c}) nicht prüfbar: {v!r}')
                if tokens[i][1] == ':':
                    nimm(':')
                    _, b = nimm()
                    (r1, c1), (r2_, c2) = zelle(a), zelle(b)
                    s += sum((wert(ws, rr, cc, tiefe + 1) for rr in range(min(r1, r2_), max(r1, r2_) + 1)
                              for cc in range(min(c1, c2), max(c1, c2) + 1)), Decimal(0))
                else:
                    s += wert(ws, *zelle(a), tiefe + 1)
                if nimm()[1] == ')':
                    return s
        raise ValueError(f'Formel in Zelle ({r},{c}) nicht prüfbar: {v!r}')

    def ausdruck() -> Decimal:
        x = summand()
        while tokens[i][1] in ('+', '-'):
            _, op = nimm()
            y = summand()
            x = x + y if op == '+' else x - y
        return x

    ergebnis = ausdruck()
    nimm('')
    return ergebnis


def main(jahr: int, template: Path | None) -> int:
    nk_dir = nk_pfade.jahresordner(jahr)
    inst = nk_pfade.datenbasis(nk_dir, jahr)
    fehler: list[str] = []

    # --- Datenbasis: Herkunft jeder Position ---
    for p in inst['positionen']:
        if not p.get('betrkv'):
            fehler.append(f'Datenbasis: Position {p.get("position")!r} ohne betrkv')
        if not (p.get('fundstelle') or p.get('berechnung')):
            fehler.append(f'Datenbasis: Position {p.get("position")!r} ohne fundstelle oder berechnung')

    soll = [(p['position'], r2(p['betrag'])) for p in inst['positionen'] if p.get('umlagefaehig')]
    summe_soll = r2(sum(b for _, b in soll))
    vz_soll = r2(nk_pfade.vorauszahlung(inst, jahr))
    nz_soll = r2(summe_soll - vz_soll)
    datum_soll = nk_pfade.abrechnungsdatum(inst, jahr).strftime('%d.%m.%Y')

    ziel = nk_pfade.eine_datei(nk_dir, '*Nebenkostenabrechnung*.xlsx')
    ws = load_workbook(ziel).worksheets[0]
    rows = nk_pfade.locate_rows(ws)

    # --- Werte ---
    ist = []
    for r in rows['slots']:
        name, betrag = ws.cell(r, 1).value, ws.cell(r, 6).value
        if nk_pfade.leer(name):
            if not nk_pfade.leer(betrag):
                fehler.append(f'Zeile {r}: Betrag {betrag!r} ohne Position')
        elif isinstance(betrag, (int, float)):
            ist.append((name, r2(betrag)))
        else:
            fehler.append(f'Zeile {r}: {name} hat keinen Betrag als Zahl, sondern {betrag!r}')
    if ist != soll:
        if [n for n, _ in ist] != [n for n, _ in soll]:
            fehler.append(f'Positionen-Namen/Reihenfolge abweichend: {ist} vs. {soll}')
        else:
            fehler += [f'{n1}: {b1} != JSON {b2}' for (n1, b1), (_, b2) in zip(ist, soll) if b1 != b2]

    if isinstance(ws.cell(rows['vz'], 6).value, str):
        fehler.append('Vorauszahlung sollte Wert, nicht Formel sein')
    for name, r, soll_wert in (('Summe', rows['summe'], summe_soll), ('Vorauszahlung', rows['vz'], vz_soll),
                               ('Ergebnis', rows['nz'], abs(nz_soll))):
        try:
            ist_wert = r2(wert(ws, r, 6))
        except ValueError as e:
            fehler.append(f'{name}: {e}')
            continue
        if ist_wert != soll_wert:
            fehler.append(f'{name} {ws.cell(r, 6).value!r} ergibt {ist_wert:.2f}, Datenbasis {soll_wert:.2f}')
    nz_text = ws.cell(rows['nz'], 1).value.strip()
    if nz_text != nk_pfade.ergebnis_text(nz_text, nz_soll):
        fehler.append(f'Ergebniszeile heißt {nz_text!r}, erwartet {nk_pfade.ergebnis_text(nz_text, nz_soll)!r}')

    # --- Format gegen Template ---
    template = nk_pfade.vorlage(nk_dir, jahr, template)
    tws = load_workbook(template).worksheets[0]
    if sorted(str(x) for x in ws.merged_cells.ranges) != sorted(str(x) for x in tws.merged_cells.ranges):
        fehler.append('merged cells unterscheiden sich vom Template')
    for col in 'ABCDEF':
        wa, wt = ws.column_dimensions[col].width, tws.column_dimensions[col].width
        if (wa or 0) != (wt or 0):
            fehler.append(f'Spaltenbreite {col}: {wa} != Template {wt}')
    for r in sorted({*(rows['slots']), rows['summe'], rows['nz']}):
        ha, ht = ws.row_dimensions[r].height, tws.row_dimensions[r].height
        if ha != ht:
            fehler.append(f'Zeilenhöhe {r}: {ha} != Template {ht}')
    for (r, c) in [(2, 5), (3, 5), (4, 6), (5, 6), (rows['datum'], 5), (rows['datum'], 6),
                   (rows['titel'], 1), (rows['einleitung'], 1),
                   (rows['slots'][0], 1), (rows['slots'][0], 6),
                   (rows['summe'], 1), (rows['summe'], 6),
                   (rows['nz'], 1), (rows['nz'], 6)]:
        ca, ct = ws.cell(r, c), tws.cell(r, c)
        if (ca.font.name, ca.font.size, ca.font.bold) != (ct.font.name, ct.font.size, ct.font.bold):
            fehler.append(f'Font ({r},{c}): {ca.font.name},{ca.font.size},b={ca.font.bold} != Template')
        if ca.number_format != ct.number_format:
            fehler.append(f'NumFmt ({r},{c}): {ca.number_format!r} != {ct.number_format!r}')

    # --- Texte: Jahreszahlen und Datum ---
    titel = str(ws.cell(rows['titel'], 1).value)
    if str(jahr) not in titel or str(jahr - 1) in titel:
        fehler.append(f'Titel nennt nicht nur das Jahr {jahr}: {titel!r}')
    einleitung = str(ws.cell(rows['einleitung'], 1).value)
    jahre = re.findall(r'für das Jahr (\d{4})', einleitung)
    if not jahre or set(jahre) != {str(jahr)}:
        fehler.append(f'Einleitung nennt nicht „für das Jahr {jahr}“: {einleitung!r}')
    datum = ws.cell(rows['datum'], 6).value
    datum_ist = datum.strftime('%d.%m.%Y') if isinstance(datum, datetime) else str(datum)
    if datum_ist != datum_soll:
        fehler.append(f'Datum {datum_ist!r} != datum_abrechnung {datum_soll}')

    if fehler:
        print('PRÜFUNG FEHLGESCHLAGEN:')
        for f in fehler:
            print(' ✗', f)
        return 1
    art = 'Guthaben' if nz_soll < 0 else 'Nachzahlung'
    print(f'Template: {template}')
    print(f'Positionen ({len(soll)}) ✓ | Summe {summe_soll:.2f} ✓ | VZ {vz_soll:.2f} ✓ | {art} {abs(nz_soll):.2f} ✓ '
          f'| Datum {datum_soll} ✓ | Format ✓ (Template)')
    print('ALLE PRÜFUNGEN BESTANDEN')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    jahr = int(sys.argv[1])
    template = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    raise SystemExit(main(jahr, template))
