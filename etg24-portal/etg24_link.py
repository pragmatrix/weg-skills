#!/usr/bin/env python3
"""Direktlinks ins ETG24-Portal: in die Abgleichliste eintragen, zu einer Datei finden und öffnen.

Aufruf:
    python3 etg24_link.py fill LISTE.json…    Direktlinks aus Exporten in die Abgleichliste eintragen
    python3 etg24_link.py DATEI…              Direktlink zu einer Datei der Ablage ausgeben (`just etg24-link`)
    python3 etg24_link.py --open DATEI…       Direktlink im Browser öffnen (`just etg24-open`)

Ein Dokument im Portal hat eine dauerhafte Adresse: die Dokumentenliste seines Bereichs mit `?document=ID`. Sie
öffnet die Vorschau des Dokuments, auch bei direktem Aufruf, sofern man im Portal angemeldet ist. Beiträge haben keine
solche Adresse.

Eine Liste ist der Export einer Dokumentenansicht mit `_etg.rows()` aus dem Skill `etg24-portal`. Jede Zeile hat dort
`id` und `url`. `fill` schreibt die Adresse als Link in die letzte Spalte „Portal“ der Abgleichliste
`Verwaltung/<Verwaltung>/ETG24-Abgleich.md`. Eine Zeile wird über Bereich, Kategorie, Titel und Datum gefunden, wie in
`etg24_abgleich.py`.

Zu einer DATEI sucht das Skript die Zeilen der Abgleichliste, deren Spalte „Ablage“ auf diese Datei verlinkt.
"""
from datetime import date
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etg24_abgleich import ABGLEICH, ROOT, full_date, section_name  # noqa: E402

CELL_SPLIT = re.compile(r"(?<!\\)\|")
LINK = re.compile(r"\]\(<([^>]+)>")


def cells(line):
    return [c.strip() for c in CELL_SPLIT.split(line)[1:-1]]


def row_line(values):
    return "| " + " | ".join(values) + " |"


def table_rows():
    """(Zeilennummer, Bereich, Zellen) für jede Datenzeile der Abgleichliste."""
    section = None
    for n, line in enumerate(ABGLEICH.read_text(encoding="utf-8").split("\n")):
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("|") and section:
            c = cells(line)
            if c and c[0] != "Kategorie" and not set(c[0]) <= {"-", ":"}:
                yield n, section, c


def fill(exports):
    urls = {}
    for path in map(Path, exports):
        section = section_name(path)
        exported = date.fromtimestamp(path.stat().st_mtime)
        for row in json.loads(path.read_text(encoding="utf-8")):
            if row.get("url"):
                urls[(section, row["category"], row["title"], full_date(row["date"], exported))] = row["url"]

    lines = ABGLEICH.read_text(encoding="utf-8").split("\n")
    for n, line in enumerate(lines):
        if line.startswith("| Kategorie") and "| Portal |" not in line:
            lines[n] = line + " Portal |"
        elif re.fullmatch(r"\|(-+\|){5}", line):
            lines[n] = line + "---|"
    filled = 0
    for n, section, c in table_rows():
        c = cells(lines[n])
        key = (section, c[0].replace("\\|", "|"), c[1].replace("\\|", "|"), c[2])
        portal = f"[öffnen](<{urls[key]}>)" if key in urls else (c[5] if len(c) > 5 else "")
        filled += key in urls
        lines[n] = row_line(c[:5] + [portal])
    ABGLEICH.write_text("\n".join(lines), encoding="utf-8")
    print(f"etg24_link: {filled} Direktlink(s) eingetragen")


def find(names, open_it):
    found = 0
    for name in names:
        target = os.path.normpath(Path(name).resolve().relative_to(ROOT))
        for _, section, c in table_rows():
            ablage = [os.path.normpath(Path(ABGLEICH.parent, urllib.parse.unquote(t)).resolve().relative_to(ROOT))
                      for t in LINK.findall(c[4])]
            url = LINK.search(c[5]).group(1) if len(c) > 5 and LINK.search(c[5]) else None
            if target in ablage and url:
                found += 1
                print(f"{name}: {url}  ({section}, {c[1]}, {c[2]})")
                if open_it:
                    subprocess.run(["open", url], check=False)
    if not found:
        sys.exit("etg24_link: kein Direktlink gefunden. Liegt die Datei im Portal, und ist die Spalte Portal gefüllt?")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if ABGLEICH is None:
        sys.exit("etg24_link: keine Abgleichliste `Verwaltung/<Verwaltung>/ETG24-Abgleich.md` im Projekt")
    if args[0] == "fill":
        fill(args[1:])
    else:
        open_it = args[0] == "--open"
        find(args[1:] if open_it else args, open_it)


if __name__ == "__main__":
    main()
