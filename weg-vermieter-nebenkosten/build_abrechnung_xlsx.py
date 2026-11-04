"""Erzeugt die Nebenkostenabrechnung (.xlsx) für `<jahr>` AUS DEM
VORJAHRESTEMPLATE — nicht durch Nachbau des Layouts.

Warum Template statt Nachbau: Ein openpyxl-Nachbau
verliert unvermutet viele Details der Vorlage (Zeilenhöhen wie die 53,25-pt-
Fußnotenzeile, `@`-Formate auf Leerezellen, right-Alignment der Betragsspalte,
verbundene Zellen, Seitenlayout, leere Nebensheets) — obwohl der Zellvergleich
deckungsgleich wirkt. Der Empfänger sieht den Unterschied sofort. Deshalb:
1) Vorjahresabrechnung nach .xlsx konvertieren (Excel/Numbers — einmalig),
2) hier nur die Zellinhalte ersetzen. Alle Formatmerkmale, Formeln
(=SUM(...), =-(Fx-Fy)) und das Page-Setup überleben das unangetastet.

Verwendung, im Projektordner:
    build_abrechnung_xlsx.py <jahr> [<template.xlsx>]

Datenbasis, Vorlage und Ausgabe folgen den Regeln in nk_pfade.py: Datenbasis und
Ausgabe in `Vermietung/<jahr>/`, Vorlage in `Vermietung/<jahr-1>/`. Liegt die
Vorlage dort nur als .xls vor, bricht das Skript ab. Nachbau ist bewusst nicht
der Fallback.
"""

import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from openpyxl import load_workbook

import nk_pfade


def r2(v) -> float:
    """Auf Cent runden — nie float-Artefakte schreiben."""
    return float(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def locate_rows(ws):
    """Findet die Ankerzeilen im Template (Spalte A: Titel, Einleitung,
    Positionsblock, Summe/Vorauszahlung/Nachzahlung; Spalte E: 'Datum:')."""
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
    if not all((titel, einleitung, summe, vz, nz, datum_r)):
        raise SystemExit(f'Template-Anker nicht gefunden: titel={titel} einleitung={einleitung} summe={summe} vz={vz} nz={nz} datum={datum_r}')
    # Positions-Slots: vom ersten belegten A/F-Block nach der Einleitung
    # lückenlos bis zur Leerzeile vor 'Summe'. Formate/Verbindungen bleiben dabei unangetastet.
    belegt = [r for r in range(einleitung + 1, summe - 1)
              if ws.cell(r, 1).value not in (None, '') or ws.cell(r, 6).value not in (None, '')]
    if not belegt:
        raise SystemExit('Keine Positionszeilen im Template gefunden.')
    slots = list(range(belegt[0], summe - 1))
    return {'titel': titel, 'einleitung': einleitung, 'slots': slots,
            'summe': summe, 'vz': vz, 'nz': nz, 'datum': datum_r}


def build(jahr: int, template: Path | None = None) -> Path:
    nk_dir = nk_pfade.jahresordner(jahr)
    inst = nk_pfade.datenbasis(nk_dir, jahr)
    pos = [(p['position'], r2(p['betrag'])) for p in inst['positionen'] if p.get('umlagefaehig')]
    vz = r2(nk_pfade.vorauszahlung(inst, jahr))

    tpl = template or nk_pfade.vorlage(nk_dir, jahr)
    wb = load_workbook(tpl)
    ws = wb.worksheets[0]
    rows = locate_rows(ws)
    vorjahr = jahr - 1

    if len(pos) > len(rows['slots']):
        raise SystemExit(f'{len(pos)} Positionen, aber Template hat nur {len(rows["slots"])} Slots.')

    # 1. Positionen eintragen, ungenutzte Slots leeren.
    for i, (name, betrag) in enumerate(pos):
        r = rows['slots'][i]
        ws.cell(r, 1).value = name
        ws.cell(r, 6).value = betrag
    for r in rows['slots'][len(pos):]:
        ws.cell(r, 1).value = None
        ws.cell(r, 6).value = None

    # 2. Texte: Vorjahr -> Abrechnungsjahr (Mietvertrag etc. bleibt unangetastet)
    y, m, d = (inst.get('datum_abrechnung') or ( inst.get('datum_abrechnung') or f'{jahr}-12-31')).split('-')
    ws.cell(rows['datum'], 6).value = f'{d}.{m}.{y}'
    titel_text = ws.cell(rows['titel'], 1).value
    ws.cell(rows['titel'], 1).value = titel_text.replace(str(vorjahr), str(jahr), 1)
    einleitung = ws.cell(rows['einleitung'], 1).value
    ws.cell(rows['einleitung'], 1).value = re.sub(r'für das Jahr \d{4}', f'für das Jahr {jahr}', einleitung)

    # 3. Vorauszahlung setzen; Summe/Nachzahlung als Formeln belassen —
    #    nur numerisch überschreiben, wenn das Template dort keine Formel hat.
    ws.cell(rows['vz'], 6).value = vz
    if not isinstance(ws.cell(rows['summe'], 6).value, str):
        ws.cell(rows['summe'], 6).value = r2(sum(b for _, b in pos))
    if not isinstance(ws.cell(rows['nz'], 6).value, str):
        ws.cell(rows['nz'], 6).value = r2(sum(b for _, b in pos) - vz)

    ziel = nk_pfade.ziel(nk_dir, jahr, tpl)
    wb.save(ziel)

    summe = r2(sum(b for _, b in pos))
    print(f'geschrieben: {ziel}')
    print(f'Template: {tpl}')
    print(f'Positionen {len(pos)} | Summe {summe:.2f} | VZ {vz:.2f} | Nachzahlung {r2(summe - vz):.2f}')
    print('Hinweis: Formeln im Template (Summe/Nachzahlung) werden erst beim '
          'Öffnen in Excel/Numbers berechnet — das verify-Skript rechnet sie nach.')
    return ziel


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    jahr = int(sys.argv[1])
    template = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    build(jahr, template)


if __name__ == '__main__':
    main()