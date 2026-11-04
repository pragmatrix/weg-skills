"""Gemeinsame Pfad-, Daten- und Vorlagenregeln von build_abrechnung_xlsx.py und verify_abrechnung_xlsx.py.

Eine Nebenkostenabrechnung des Jahres JJJJ liegt in `Vermietung/JJJJ/` des Projektordners. Den Projektordner
bestimmt `projekt.py` aus dem Skill weg-eigentuemer-ablage. Im Jahresordner liegen genau eine Datenbasis
`nebenkostenabrechnung_JJJJ_<Mieter>.json` und nach dem Bauen die Excel-Abrechnung. Die Vorlage ist die Excel-Abrechnung
des Vorjahres in `Vermietung/<JJJJ-1>/`.
"""

import json
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Den Projektordner bestimmt der Skill weg-eigentuemer-ablage.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "weg-eigentuemer-ablage" / "scripts"))
from projekt import projektordner  # noqa: E402

# Texte in Spalte A der Ergebniszeile. Ist das Ergebnis negativ, bekommt der Mieter Geld zurück.
NACHZAHLUNG = 'Ihre Nachzahlung'
GUTHABEN = 'Ihr Guthaben'


def jahresordner(jahr: int) -> Path:
    return projektordner() / 'Vermietung' / str(jahr)


def eine_datei(ordner: Path, muster: str) -> Path:
    treffer = sorted(ordner.glob(muster))
    if len(treffer) != 1:
        raise SystemExit(f'ABBRUCH: In {ordner} passt {"keine" if not treffer else "mehr als eine"} Datei auf '
                         f'{muster}: {[t.name for t in treffer]}')
    return treffer[0]


def datenbasis(ordner: Path, jahr: int) -> dict:
    return json.loads(eine_datei(ordner, f'nebenkostenabrechnung_{jahr}_*.json').read_text(encoding='utf-8'))


def vorauszahlung(inst: dict, jahr: int) -> float:
    """Vorauszahlungen des Mieters im Jahr, aus `summen.vorauszahlung`."""
    summen = inst['summen']
    if f'vorauszahlung_{jahr}' in summen:
        raise SystemExit(f'ABBRUCH: Die Datenbasis nennt die Vorauszahlung noch unter dem alten Schlüssel '
                         f'summen.vorauszahlung_{jahr}. Den Schlüssel in summen.vorauszahlung umbenennen.')
    if 'vorauszahlung' not in summen:
        raise SystemExit('ABBRUCH: In der Datenbasis fehlt summen.vorauszahlung.')
    return summen['vorauszahlung']


def abrechnungsdatum(inst: dict, jahr: int) -> date:
    """Datum der Abrechnung aus `datum_abrechnung` (JJJJ-MM-TT). Eine Abrechnung entsteht erst nach dem Jahr."""
    text = inst.get('datum_abrechnung')
    if not text:
        raise SystemExit('ABBRUCH: In der Datenbasis fehlt datum_abrechnung (JJJJ-MM-TT).')
    try:
        datum = date.fromisoformat(text)
    except ValueError:
        raise SystemExit(f'ABBRUCH: datum_abrechnung {text!r} ist kein Datum der Form JJJJ-MM-TT.')
    if datum <= date(jahr, 12, 31):
        raise SystemExit(f'ABBRUCH: datum_abrechnung {text} liegt nicht nach dem Abrechnungsjahr {jahr}.')
    return datum


def r2(v) -> float:
    """Betrag auf Cent gerundet. Ein Wert, der keine Zahl ist, bricht mit InvalidOperation ab."""
    return float(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def leer(v) -> bool:
    return v in (None, '')


def locate_rows(ws) -> dict:
    """Findet die Ankerzeilen der Vorlage. Spalte A trägt Titel, Einleitung, „Summe“, „Ihre Vorauszahlung“ und
    „Ihre Nachzahlung“ oder „Ihr Guthaben“. Spalte E trägt „Datum:“.

    Die Positionszeilen (Slots) reichen von der ersten belegten Zeile nach der Einleitung bis zur Zeile vor der
    Leerzeile über „Summe“. Diese Leerzeile muss leer sein, sonst bliebe dort eine Position des Vorjahres stehen.
    """
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
            elif s.startswith((NACHZAHLUNG, GUTHABEN)):
                nz = r
        if ws.cell(r, 5).value == 'Datum:' and datum_r is None:
            datum_r = r
    if not all((titel, einleitung, summe, vz, nz, datum_r)):
        raise SystemExit(f'ABBRUCH: Anker der Vorlage nicht gefunden: titel={titel} einleitung={einleitung} '
                         f'summe={summe} vz={vz} nz={nz} datum={datum_r}')
    if not (leer(ws.cell(summe - 1, 1).value) and leer(ws.cell(summe - 1, 6).value)):
        raise SystemExit(f'ABBRUCH: Zeile {summe - 1} direkt über „Summe“ ist nicht leer. Die Vorlage braucht dort '
                         f'eine Leerzeile, damit keine Position des Vorjahres in der Summe stehen bleibt.')
    belegt = [r for r in range(einleitung + 1, summe - 1)
              if not leer(ws.cell(r, 1).value) or not leer(ws.cell(r, 6).value)]
    if not belegt:
        raise SystemExit('ABBRUCH: Keine Positionszeilen in der Vorlage gefunden.')
    return {'titel': titel, 'einleitung': einleitung, 'slots': list(range(belegt[0], summe - 1)),
            'summe': summe, 'vz': vz, 'nz': nz, 'datum': datum_r}


def ergebnis_text(alt: str, ergebnis: float) -> str:
    """Text der Ergebniszeile für das neue Ergebnis. Ein Zusatz hinter dem Text der Vorlage bleibt erhalten."""
    rest = alt.strip().removeprefix(NACHZAHLUNG).removeprefix(GUTHABEN)
    return (GUTHABEN if ergebnis < 0 else NACHZAHLUNG) + rest


def vorlage(ordner: Path, jahr: int, angegeben: Path | None = None) -> Path:
    """Excel-Abrechnung des Vorjahres, oder die angegebene Datei. Liegt die Vorjahresabrechnung nur als .xls vor,
    bricht das Skript ab, statt das Layout nachzubauen (siehe SKILL.md, Template-Verfahren)."""
    if angegeben is not None:
        if not angegeben.is_file():
            raise SystemExit(f'ABBRUCH: Die angegebene Vorlage {angegeben} gibt es nicht.')
        return angegeben
    vorjahr_dir = ordner.parent / str(jahr - 1)
    kandidaten = sorted(vorjahr_dir.glob('*Nebenkostenabrechnung*.xlsx'))
    if kandidaten:
        return kandidaten[0]
    if list(vorjahr_dir.glob('*Nebenkostenabrechnung*.xls')):
        raise SystemExit(
            f'ABBRUCH: In {vorjahr_dir} liegt die Vorjahresabrechnung nur als .xls vor.\n'
            f'Die Datei einmal in Excel oder Numbers nach .xlsx konvertieren oder die Vorlage als Argument übergeben.')
    raise SystemExit(f'ABBRUCH: Keine Vorlage in {vorjahr_dir}. Die Vorlage als Argument übergeben.')


def ziel(ordner: Path, jahr: int, vorlage_pfad: Path) -> Path:
    """Name der neuen Abrechnung: der Name der Vorlage mit dem neuen Jahr."""
    name = vorlage_pfad.name.replace(str(jahr - 1), str(jahr))
    return ordner / (name if name != vorlage_pfad.name else f'{jahr} Nebenkostenabrechnung.xlsx')
