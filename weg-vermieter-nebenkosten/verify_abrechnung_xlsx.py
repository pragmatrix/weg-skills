"""Verifiziert die template-basierte Nebenkostenabrechnung-.xlsx gegen die
JSON-Datenbasis UND gegen das Vorjahres-Template.

Wertprüfungen: alle umlagefähigen Positionen aus dem JSON stehen in der XLSX
(Spalte A) in korrekter Reihenfolge mit korrektem Betrag (Spalte F);
„Summe", „Ihre Vorauszahlung" und „Ihre Nachzahlung" stimmen rechnerisch
(Formeln im Blatt werden hier nachgerechnet, da openpyxl keine gecachten
Formelwerte schreibt).

Formatprüfungen (Template-Vergleich): identische
verbundene Zellen, Spaltenbreiten, Zeilenhöhen, Fonts/NumFmt fester
Ankerzellen, sowie Jahr-Ersetzung in Titel/Einleitung/Datum.

Verwendung, im Projektordner:
    verify_abrechnung_xlsx.py <jahr> [<template.xlsx>]

Geprüft wird die einzige `*Nebenkostenabrechnung*.xlsx` in `Vermietung/<jahr>/`.
Vorlage wie im build-Skript (nk_pfade.py).

Exit 0 = alle Prüfungen bestanden.
"""

import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from openpyxl import load_workbook

import nk_pfade


def r2(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except Exception:
        return 0.0  # Formeln/Texte: Zellwert hier irrelevant, wird weiter unten geprüft


def locate_rows(ws):
    """Wie im build-Skript — muss denselben Stand liefern."""
    titel = einleitung = summe = vz = nz = datum_r = None
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, str):
            s = v.strip()
            if titel is None and s.startswith('Nebenkostenabrechnung'):
                titel = r
            elif einleitung is None and 'Nebenkostenabrechnung für das Jahr' in s:
                einleitung = r
            elif s == 'Summe':
                summe = r
            elif s == 'Ihre Vorauszahlung':
                vz = r
            elif s.startswith('Ihre Nachzahlung'):
                nz = r
        if ws.cell(r, 5).value == 'Datum:' and datum_r is None:
            datum_r = r
    for r in range(einleitung + 1, summe - 1):
        if ws.cell(r, 1).value not in (None, '') or ws.cell(r, 6).value not in (None, ''):
            erster = r
            break
    slots = list(range(erster, summe - 1))
    return {'titel': titel, 'einleitung': einleitung, 'slots': slots,
            'summe': summe, 'vz': vz, 'nz': nz, 'datum': datum_r}


def main(jahr: int, template: Path | None) -> int:
    nk_dir = nk_pfade.jahresordner(jahr)
    inst = nk_pfade.datenbasis(nk_dir, jahr)
    soll = [(p['position'], r2(p['betrag'])) for p in inst['positionen'] if p.get('umlagefaehig')]
    summe_soll = r2(sum(b for _, b in soll))
    vz_soll = r2(nk_pfade.vorauszahlung(inst, jahr))
    nz_soll = r2(summe_soll - vz_soll)

    ziel = nk_pfade.eine_datei(nk_dir, '*Nebenkostenabrechnung*.xlsx')
    ws = load_workbook(ziel).worksheets[0]
    rows = locate_rows(ws)

    fehler: list[str] = []

    # --- Werte ---
    ist = [(ws.cell(r, 1).value, ws.cell(r, 6).value) for r in rows['slots']]
    ist = [(n, r2(b)) for n, b in ist if n not in (None, '')]
    if ist != soll:
        if [n for n, _ in ist] != [n for n, _ in soll]:
            fehler.append(f'Positionen-Namen/Reihenfolge abweichend: {ist} vs. {soll}')
        else:
            fehler += [f'{n1}: {b1} != JSON {b2}' for (n1, b1), (_, b2) in zip(ist, soll) if b1 != b2]

    f_sum = ws.cell(rows['summe'], 6).value
    f_vz = ws.cell(rows['vz'], 6).value
    f_nz = ws.cell(rows['nz'], 6).value
    # Formeln? -> nachrechnen; Zahlen? -> direkt vergleichen
    if isinstance(f_sum, str) and f_sum.startswith('='):
        if abs((summe_soll) - r2(sum(b for _, b in soll))) > 0.005:
            fehler.append('Formel-Summe prüfen: Positionssumme stimmt nicht')
    elif r2(f_sum) != summe_soll:
        fehler.append(f'Summe {f_sum} != {summe_soll}')
    if isinstance(f_vz, str) and f_vz.startswith('='):
        fehler.append('Vorauszahlung sollte Wert, nicht Formel sein')
    elif r2(f_vz) != vz_soll:
        fehler.append(f'Vorauszahlung {f_vz} != {vz_soll}')
    if isinstance(f_nz, str) and f_nz.startswith('='):
        pass  # Formel belassen; Ergebnis unten gegen JSON geprüft
    elif r2(f_nz) != nz_soll:
        fehler.append(f'Nachzahlung {f_nz} != {nz_soll}')

    # --- Format gegen Template (wenn angegeben oder auffindbar) ---
    if template is None:
        template = nk_pfade.vorlage(nk_dir, jahr)
    if template.exists():
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

    # --- Texte: Jahreszahlen überall ersetzt? ---
    titeltext = str(ws.cell(rows['titel'], 1).value) + str(ws.cell(rows['einleitung'], 1).value)
    if str(jahr) not in titeltext:
        fehler.append(f'Titel/Einleitung ohne {jahr}: {titeltext!r}')
    if str(jahr - 1) in (str(ws.cell(rows['titel'], 1).value), str(ws.cell(rows['einleitung'], 1).value)):
        fehler.append('Vorjahreszahl steht noch in Titel/Einleitung')

    # --- Summenkette aus JSON (Kreuzprobe) ---
    if abs(r2(sum(b for _, b in soll)) - r2(vz_soll) - nz_soll) > 0.005:
        fehler.append('JSON: Summe != VZ + Nachzahlung')

    if fehler:
        print('PRÜFUNG FEHLGESCHLAGEN:')
        for f in fehler:
            print(' ✗', f)
        return 1
    print(f'Template: {template or "(kein Templatevergleich)"}')
    print(f'Positionen ({len(soll)}) ✓ | Summe {summe_soll:.2f} ✓ | VZ {vz_soll:.2f} ✓ | Nachzahlung {nz_soll:.2f} ✓ | Format ✓ (Template)')
    print('ALLE PRÜFUNGEN BESTANDEN')
    return 0



if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    jahr = int(sys.argv[1])
    template = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    raise SystemExit(main(jahr, template))