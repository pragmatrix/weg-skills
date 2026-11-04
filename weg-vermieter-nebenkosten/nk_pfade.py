"""Gemeinsame Pfad- und Datenregeln von build_abrechnung_xlsx.py und verify_abrechnung_xlsx.py.

Eine Nebenkostenabrechnung des Jahres JJJJ liegt in `Vermietung/JJJJ/` des Projektordners. Der Projektordner ist die
Git-Wurzel des aktuellen Verzeichnisses. Im Jahresordner liegen genau eine Datenbasis
`nebenkostenabrechnung_JJJJ_<Mieter>.json` und nach dem Bauen die Excel-Abrechnung. Die Vorlage ist die Excel-Abrechnung
des Vorjahres in `Vermietung/<JJJJ-1>/`.
"""

import json
import subprocess
from pathlib import Path


def projektordner() -> Path:
    out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit('ABBRUCH: Das aktuelle Verzeichnis liegt in keinem Git-Repository (Projektordner).')
    return Path(out.stdout.strip())


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
    """Vorauszahlungen der Mieter im Jahr. Ältere Datenbasen tragen das Jahr im Schlüssel."""
    summen = inst['summen']
    return summen[f'vorauszahlung_{jahr}'] if f'vorauszahlung_{jahr}' in summen else summen['vorauszahlung']


def vorlage(ordner: Path, jahr: int) -> Path:
    """Excel-Abrechnung des Vorjahres. Liegt sie nur als .xls vor, bricht das Skript ab, statt das Layout
    nachzubauen (siehe SKILL.md, Template-Verfahren)."""
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
