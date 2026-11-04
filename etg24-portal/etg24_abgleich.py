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

Das Portal schreibt Daten des laufenden Jahres ohne Jahr („18. September“) und die Daten der letzten beiden Tage als
„heute“ und „gestern“. Das Skript rechnet sie vom Tag aus, an dem die Liste exportiert wurde, und gibt jedes Datum als
TT.MM.JJJJ aus.
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
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]


def section_name(path):
    """`objekt.json` → „Objekt“, `einheit-4.json` → „Einheit 4“."""
    return path.stem.replace("-", " ").capitalize()


def full_date(text, exported):
    """Datum aus dem Portal als TT.MM.JJJJ. `exported` ist der Tag des Exports."""
    if text in ("heute", "gestern"):
        return (exported - timedelta(days=text == "gestern")).strftime("%d.%m.%Y")
    m = re.fullmatch(r"(\d{1,2})\. (\w+)", text)
    if m and m.group(2) in MONATE:
        return f"{int(m.group(1)):02d}.{MONATE.index(m.group(2)) + 1:02d}.{exported.year}"
    return text


def portal_size(n):
    """Größe so gerundet, wie das Portal sie anzeigt."""
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{round(n / 1000)} kB"


def known():
    """Schlüssel (Bereich, Kategorie, Titel, Datum) aller Zeilen der Abgleichliste."""
    keys, section = set(), None
    for line in ABGLEICH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("|") and section:
            cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)[1:-1]]
            if len(cells) >= 3 and not set(cells[0]) <= {"-", ":"}:
                keys.add((section, cells[0], cells[1], cells[2]))
    return keys


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    keys = known() if ABGLEICH else set()
    by_size = {}
    for rel in files(ignore_patterns()):
        by_size.setdefault(portal_size((ROOT / rel).stat().st_size), []).append(rel)

    for path in map(Path, sys.argv[1:]):
        section = section_name(path)
        exported = date.fromtimestamp(path.stat().st_mtime)
        new = []
        for row in json.loads(path.read_text(encoding="utf-8")):
            key = (section, row["category"], row["title"], full_date(row["date"], exported))
            if key not in keys:
                # Ältere Exporte haben noch keinen Dateityp. Dann zählt jede Datei gleicher Größe.
                suffix = "." + row["type"] if row.get("type") else None
                same = [c for c in by_size.get(row["size"], []) if suffix in (None, c.suffix.lower())]
                candidates = ", ".join(f"`{c.as_posix()}`" for c in same) or "–"
                portal = f"[öffnen](<{row['url']}>)" if row.get("url") else ""
                cells = [*key[1:], row["size"], candidates, portal]
                new.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
        print(f"## {section}: {len(new)} neu")
        for line in new:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
