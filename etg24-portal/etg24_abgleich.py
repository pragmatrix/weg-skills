#!/usr/bin/env python3
"""Nennt die Dokumente im ETG24-Portal, die noch nicht in der Abgleichliste stehen.

Aufruf:
    python3 etg24_abgleich.py LISTE.json…

Eine Liste ist der Export einer Dokumentenansicht des Portals (`_etg.rows()` aus dem Skill
`etg24-portal`). Der Dateiname nennt den Bereich: `objekt.json` für die Objektdokumente,
`einheit-4.json` für die Dokumente von Einheit 4.

Die Abgleichliste `Verwaltung/<Verwaltung>/ETG24-Abgleich.md` hat je Bereich einen Abschnitt (`## Objekt`,
`## Einheit 4`) mit einer Tabelle. Ein Dokument ist dort bekannt, wenn Kategorie, Titel und Datum übereinstimmen.
Für jedes unbekannte Dokument gibt das Skript eine fertige Tabellenzeile aus. In der fünften Spalte stehen Dateien
der Ablage mit derselben Größe und Endung als Kandidaten. Danach folgt die Spalte „Portal“ mit dem Direktlink
zum Dokument, wenn der Export ihn enthält (siehe `etg24_link.py`). Das Portal rundet die Größe dezimal, etwa 698175 Bytes
zu „698 kB“.
Ob ein Kandidat wirklich dasselbe Dokument ist, klärt erst der Download mit `just dup`.

Das Portal schreibt ältere Daten als TT.MM.JJJJ, jüngere ohne Jahr („18. September“) und die Daten der letzten
beiden Tage als „heute“ und „gestern“. Das Skript rechnet sie vom Tag aus, an dem die Liste exportiert wurde, und gibt
jedes Datum als TT.MM.JJJJ aus. Ein Datum ohne Jahr, das nach dem Exporttag läge, gehört ins Vorjahr. Ein anderes
Format bricht das Skript ab, damit kein Dokument mit falschem Datum als neu gilt.

Ein wiederholter Export bekommt vom Empfänger einen Zähler im Namen, etwa `objekt (2).json`. Der Zähler zählt nicht
zum Bereich. Exporte desselben Bereichs ergeben einen gemeinsamen Abschnitt der Ausgabe, in dem jedes Dokument einmal
steht.
"""
from datetime import date, timedelta
from pathlib import Path
import json
import re
import sys

# `find_dupes.py` gehört zum Skill `weg-eigentuemer-ablage`, der neben diesem Skill installiert ist.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "weg-eigentuemer-ablage" / "scripts"))
from find_dupes import ROOT, files, ignore_patterns  # noqa: E402


def abgleichliste():
    """Die Abgleichliste im Ordner der Verwaltung, die das Portal betreibt. Es darf nur eine geben."""
    found = sorted(ROOT.glob("Verwaltung/*/ETG24-Abgleich.md"))
    if len(found) > 1:
        sys.exit("Mehr als eine Abgleichliste: " + ", ".join(str(p.relative_to(ROOT)) for p in found))
    return found[0] if found else None


ABGLEICH = abgleichliste()
COLUMNS = ["Kategorie", "Titel im Portal", "Datum", "Größe", "Ablage", "Portal"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]


def section_name(path):
    """`objekt.json` → „Objekt“, `einheit-4.json` und `einheit-4 (2).json` → „Einheit 4“."""
    return re.sub(r" \(\d+\)$", "", path.stem).replace("-", " ").capitalize()


def full_date(text, exported):
    """Datum aus dem Portal als TT.MM.JJJJ. `exported` ist der Tag des Exports."""
    if text in ("heute", "gestern"):
        return (exported - timedelta(days=text == "gestern")).strftime("%d.%m.%Y")
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", text):
        return text
    m = re.fullmatch(r"(\d{1,2})\. (\w+)", text)
    if m and m.group(2) in MONATE:
        # Das jüngste gültige Datum, das nicht nach dem Exporttag liegt. Ein 29. Februar kann so ins Vorjahr fallen.
        for year in (exported.year, exported.year - 1):
            try:
                day = date(year, MONATE.index(m.group(2)) + 1, int(m.group(1)))
            except ValueError:
                continue
            if day <= exported:
                return day.strftime("%d.%m.%Y")
        sys.exit(f"Datum im Export „{text}“ liegt weder im Jahr des Exports noch im Vorjahr am oder vor dem Exporttag "
                 f"{exported.strftime('%d.%m.%Y')}.")
    sys.exit(f"Unbekanntes Datumsformat im Export: „{text}“. Erwartet TT.MM.JJJJ, „D. Monat“, heute oder gestern.")


def table_rows(lines):
    """(Zeilennummer, Bereich, Zellen) für jede Datenzeile einer Dokumententabelle der Abgleichliste.

    Eine Dokumententabelle beginnt mit der Kopfzeile `| Kategorie …` unter einem Abschnitt `## <Bereich>`. Andere
    Tabellen zählen nicht. Die Zellen bleiben maskiert (`\\|`), damit eine Zeile unverändert zurückgeschrieben werden
    kann. Eine Kopfzeile mit anderen Spalten als `COLUMNS` und eine Zeile mit einer anderen Zahl von Zellen brechen ab.
    Die Trennzeile unter der Kopfzeile besteht nur aus Zellen mit `-` und `:`. Eine Datenzeile mit leerer erster Zelle,
    etwa ein Dokument ohne Kategorie, ist keine Trennzeile.
    """
    section, in_table = None, False
    for n, line in enumerate(lines):
        where = f"{ABGLEICH.name}, Zeile {n + 1}"
        if line.startswith("## "):
            section, in_table = line[3:].strip(), False
        elif not line.startswith("|"):
            in_table = False
        elif line.startswith("| Kategorie") and section:
            if cells(line) != COLUMNS:
                sys.exit(f"{where}: Kopfzeile erwartet „| {' | '.join(COLUMNS)} |“")
            in_table = True
        elif in_table:
            c = cells(line)
            if c and all(x and set(x) <= {"-", ":"} for x in c):
                continue
            if len(c) != len(COLUMNS):
                sys.exit(f"{where}: {len(c)} statt {len(COLUMNS)} Zellen")
            yield n, section, c


def cells(line):
    """Zellen einer Tabellenzeile, ohne die Ränder. Ein maskiertes `\\|` trennt nicht."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def unescape(cell):
    return cell.replace("\\|", "|")


def portal_size(n):
    """Größe so gerundet, wie das Portal sie anzeigt."""
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{round(n / 1000)} kB"


def known():
    """Schlüssel (Bereich, Kategorie, Titel, Datum) aller Zeilen der Abgleichliste."""
    lines = ABGLEICH.read_text(encoding="utf-8").splitlines()
    return {(section, unescape(c[0]), unescape(c[1]), c[2]) for _, section, c in table_rows(lines)}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    keys = known() if ABGLEICH else set()
    by_size = {}
    for rel in files(ignore_patterns()):
        by_size.setdefault(portal_size((ROOT / rel).stat().st_size), []).append(rel)

    # Neue Zeilen je Bereich, nach Schlüssel. Ein Dokument aus mehreren Exporten desselben Bereichs steht so einmal da.
    new = {}
    for path in map(Path, sys.argv[1:]):
        section = section_name(path)
        exported = date.fromtimestamp(path.stat().st_mtime)
        lines = new.setdefault(section, {})
        for row in json.loads(path.read_text(encoding="utf-8")):
            key = (section, row["category"], row["title"], full_date(row["date"], exported))
            if key not in keys and key not in lines:
                same = [c for c in by_size.get(row["size"], []) if c.suffix.lower() == "." + row["type"]]
                candidates = ", ".join(f"`{c.as_posix()}`" for c in same) or "–"
                portal = f"[öffnen](<{row['url']}>)" if row.get("url") else ""
                values = [*key[1:], row["size"], candidates, portal]
                lines[key] = "| " + " | ".join(v.replace("|", "\\|") for v in values) + " |"
    for section, lines in new.items():
        print(f"## {section}: {len(lines)} neu")
        for line in lines.values():
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
