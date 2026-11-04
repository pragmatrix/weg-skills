"""Erzeugt die Nebenkostenabrechnung (.xlsx) für `<jahr>` aus der Abrechnung des Vorjahres als Vorlage. Warum das
Skript nur Zellinhalte ersetzt und das Layout nie nachbaut, steht in SKILL.md, Abschnitt „Template-Verfahren“.

Verwendung, im Projektordner:
    build_abrechnung_xlsx.py <jahr> [<template.xlsx>]

Datenbasis, Vorlage und Ausgabe folgen den Regeln in nk_pfade.py: Datenbasis und
Ausgabe in `Vermietung/<jahr>/`, Vorlage in `Vermietung/<jahr-1>/`. Liegt die
Vorlage dort nur als .xls vor, bricht das Skript ab. Nachbau ist bewusst nicht
der Fallback.
"""

import re
import sys
from pathlib import Path

from openpyxl import load_workbook

import nk_pfade
from nk_pfade import r2


def build(jahr: int, template: Path | None = None) -> Path:
    nk_dir = nk_pfade.jahresordner(jahr)
    inst = nk_pfade.datenbasis(nk_dir, jahr)
    pos = [(p['position'], r2(p['betrag'])) for p in inst['positionen'] if p.get('umlagefaehig')]
    vz = r2(nk_pfade.vorauszahlung(inst, jahr))
    datum = nk_pfade.abrechnungsdatum(inst, jahr)

    tpl = nk_pfade.vorlage(nk_dir, jahr, template)
    wb = load_workbook(tpl)
    ws = wb.worksheets[0]
    rows = nk_pfade.locate_rows(ws)
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
    ws.cell(rows['datum'], 6).value = datum.strftime('%d.%m.%Y')
    titel_text = ws.cell(rows['titel'], 1).value
    ws.cell(rows['titel'], 1).value = titel_text.replace(str(vorjahr), str(jahr), 1)
    einleitung = ws.cell(rows['einleitung'], 1).value
    ws.cell(rows['einleitung'], 1).value = re.sub(r'für das Jahr \d{4}', f'für das Jahr {jahr}', einleitung)

    # 3. Vorauszahlung setzen. Hat die Vorlage bei Summe und Ergebnis Formeln, schreibt das Skript Formeln über
    #    die neuen Slots, sonst Zahlen. Ein Guthaben steht als positiver Betrag unter „Ihr Guthaben“.
    summe = r2(sum(b for _, b in pos))
    ergebnis = r2(summe - vz)
    f_slots = f'F{rows["slots"][0]}:F{rows["slots"][-1]}'
    f_summe, f_vz = f'F{rows["summe"]}', f'F{rows["vz"]}'
    ws.cell(rows['vz'], 6).value = vz
    if isinstance(ws.cell(rows['summe'], 6).value, str):
        ws.cell(rows['summe'], 6).value = f'=SUM({f_slots})'
    else:
        ws.cell(rows['summe'], 6).value = summe
    if isinstance(ws.cell(rows['nz'], 6).value, str):
        ws.cell(rows['nz'], 6).value = f'={f_vz}-{f_summe}' if ergebnis < 0 else f'={f_summe}-{f_vz}'
    else:
        ws.cell(rows['nz'], 6).value = abs(ergebnis)
    ws.cell(rows['nz'], 1).value = nk_pfade.ergebnis_text(ws.cell(rows['nz'], 1).value, ergebnis)

    ziel = nk_pfade.ziel(nk_dir, jahr, tpl)
    wb.save(ziel)

    print(f'geschrieben: {ziel}')
    print(f'Template: {tpl}')
    art = 'Guthaben' if ergebnis < 0 else 'Nachzahlung'
    print(f'Positionen {len(pos)} | Summe {summe:.2f} | VZ {vz:.2f} | {art} {abs(ergebnis):.2f}')
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
