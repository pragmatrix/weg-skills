#!/usr/bin/env python3
"""Warnt bei Fakten ohne Quellenlink in eigenen Markdown-Dateien.

Aufruf:
    python3 check_unbelegt.py [--alle] [DATEI...]    (`just unbelegt [--alle] [DATEI...]`)

Ohne DATEI prüft das Skript die eigenen MDs, die gegenüber HEAD neu oder geändert sind. Die Regel dazu steht im
Abschnitt „Quellenlinks“ des Skills `weg-eigentuemer-ablage`: Jeder Fakt trägt einen Quellenlink.

Gemeldet werden nur Blöcke, die gegenüber HEAD neu sind oder sich inhaltlich geändert haben. Fettdruck und
Zeilenumbrüche zählen dabei nicht als Änderung. So gehen neue Lücken nicht unter alten Lücken einer Datei unter, die
nur an anderer Stelle bearbeitet wurde. `--alle` meldet jeden Block ohne Beleg, auch die alten.

Das Skript sucht nach Fakten, die es an ihrer Form erkennt: Beträge in Euro oder Cent, Prozentwerte und Daten wie
22.05.2023. Ein Block mit einem solchen Fakt gilt als belegt, wenn er einen Link oder eine „eigene Rechnung“ enthält.
Ein Block ist ein Absatz, ein Listenpunkt oder eine Tabellenzeile. Eine Tabelle gilt als belegt, wenn der Absatz
direkt davor oder ihre Kopfzeile einen Link hat. Überschriften, Zitatblöcke (`>`, etwa wörtliche Zitate aus einem
Dokument), Codeblöcke, die Kopfzeile „Stand:“ und erzeugte Text-MDs zählen nicht. Aussagen ohne Zahl findet das
Skript nicht.

Das Ergebnis ist nur ein Hinweis, der Exit-Code ist immer 0. Ob ein Block wirklich einen Beleg braucht, entscheidet
der Mensch, etwa bei einer Frist, die sich aus dem Gesetz ergibt.
"""
import re
import subprocess
import sys
from pathlib import Path

from check_links import FENCE, MARKER, ROOT, blank
from projekt import skipped

FACT = re.compile(r"\d[\d.]*(?:,\d+)?\s?(?:€|EUR|Euro|ct/kWh|%)|\b\d{1,2}\.\d{1,2}\.\d{4}\b")
CITED = re.compile(r"\]\(|eigene Rechnung", re.I)
ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s|^\s*\|")


def blocks(text):
    """(Zeilennummer, Text) je Absatz, Listenpunkt oder Tabellenzeile. Eingerückte Folgezeilen gehören dazu."""
    current, start = [], 0
    for n, line in enumerate(FENCE.sub(blank, text).split("\n"), 1):
        stripped = line.strip()
        new_item = ITEM.match(line) is not None
        if not stripped or stripped.startswith(("#", ">")) or new_item:
            if current:
                yield start, " ".join(current)
            current, start = [], n
            if new_item:
                current = [stripped]
            continue
        if not current:
            start = n
        current.append(stripped)
    if current:
        yield start, " ".join(current)


def content(block):
    """Inhalt eines Blocks ohne Fettdruck und mit einfachen Leerzeichen, zum Vergleich mit HEAD."""
    return " ".join(block.replace("*", "").split())


def head_blocks(rel):
    """Inhalte der Blöcke von `rel` in HEAD. Eine Datei, die in HEAD fehlt, hat keine."""
    out = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{rel}"], capture_output=True, text=True)
    return {content(b) for _, b in blocks(out.stdout)} if out.returncode == 0 else set()


def changed_files():
    """Neue und geänderte MDs, je mit ihrem Pfad in HEAD. Bei einer Umbenennung ist das der alte Pfad, damit der
    unveränderte Inhalt nicht als neu gilt. Mit -z folgt der alte Pfad als eigener Eintrag ohne Status."""
    out = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "-z", "--untracked-files=all"],
                         capture_output=True, check=True, text=True).stdout
    entries = iter(out.split("\0"))
    files = []
    for e in entries:
        if not e:
            continue
        status, name = e[:2], e[3:]
        head_rel = next(entries) if status[0] in "RC" else name
        if "D" not in status and name.endswith(".md") and not skipped(Path(name)):
            files.append((ROOT / name, head_rel))
    return files


def main():
    args = sys.argv[1:]
    report_all = "--alle" in args
    given = [Path(a).resolve() for a in args if a != "--alle"]
    files = [(p, p.relative_to(ROOT).as_posix()) for p in given] or changed_files()
    count = 0
    for path, head_rel in files:
        text = path.read_text(encoding="utf-8")
        if text.startswith(MARKER):
            continue
        rel = path.relative_to(ROOT).as_posix()
        old = set() if report_all else head_blocks(head_rel)
        previous, table_cited = "", False
        for line, block in blocks(text):
            if block.startswith("|"):
                # Eine Tabelle gilt als belegt, wenn der Absatz davor oder ihre Kopfzeile einen Link hat.
                if not previous.startswith("|"):
                    table_cited = bool(CITED.search(previous) or CITED.search(block))
            previous = block
            if block.startswith("Stand:") or set(block) <= set("|-: ") or (block.startswith("|") and table_cited):
                continue
            fact = FACT.search(block)
            if fact and not CITED.search(block) and content(block) not in old:
                count += 1
                print(f"{rel}:{line}: ohne Quellenlink: …{block[max(0, fact.start() - 50):fact.end() + 30]}…")
    print(f"check_unbelegt: {count} Block/Blöcke mit Fakt ohne Quellenlink" if count
          else "check_unbelegt: jeder erkannte Fakt hat einen Quellenlink")


if __name__ == "__main__":
    main()
