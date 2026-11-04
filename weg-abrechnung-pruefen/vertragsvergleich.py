#!/usr/bin/env python3
"""Vergleicht zwei Fassungen eines Vertrags Satz für Satz und gibt jede geänderte Stelle aus.

Aufruf:
    python3 vertragsvergleich.py ALT.pdf NEU.pdf > tmp/vergleich.txt
    just vergleich ALT.pdf NEU.pdf

Die Text-MDs neben den PDFs taugen dafür nicht. Sie behalten das Layout und mischen bei zweispaltigen Verträgen
(Grundleistungen links, besondere Leistungen rechts) beide Spalten Zeile für Zeile. Das Skript liest den Text deshalb
mit `pdftotext` ohne `-layout`, also Spalte für Spalte in Lesereihenfolge.

Vor dem Vergleich entfernt es Kopf- und Fußzeilen, Seitenzahlen und Silbentrennungen. Eine Kopf- oder Fußzeile ist
eine Zeile unter den ersten oder letzten drei Zeilen einer Seite, die dort auf mindestens drei Seiten gleich vorkommt.
Gezählt werden die Seiten beider Fassungen zusammen, damit beide dieselben Zeilen verlieren. Kurze Tabellenzellen wie
„inklusive“ in der Mitte einer Seite bleiben so erhalten. Eine Silbentrennung wird nur am Zeilenende aufgehoben. Folgt
auf den Bindestrich ein Wort wie „und“ oder „oder“, ist er ein Ergänzungsstrich und bleibt stehen („Grund- und
besondere Leistungen“). Dann teilt das Skript den Text in Sätze und vergleicht die Satzfolgen.

Jede geänderte Stelle beginnt mit `===`. Darunter stehen die Sätze der alten Fassung mit `-` und die der neuen mit `+`.
Steht ein Satz in beiden Fassungen, aber an anderer Stelle, erscheint er als `-` und als `+`. Fundstellen mit Seite
schlägt man danach in den Text-MDs nach.
"""
from collections import Counter
import difflib
import re
import subprocess
import sys

SENTENCE = re.compile(r"(?<=[.:;!?])\s+(?=[A-ZÄÖÜ„(\d])|\s(?=\d\.\d(?:\.\d+)?\s)")
NOISE = {"", "-", "•", "·", "☐", "☒"}
# So viele Zeilen am Anfang und am Ende einer Seite kommen als Kopf- oder Fußzeile in Frage.
RAND = 3
# Nach einem Ergänzungsstrich („Grund- und“) folgt eines dieser Wörter. Dort ist der Bindestrich keine Silbentrennung.
BINDEWOERTER = {"und", "oder", "bis", "sowie", "bzw."}


def pages(pdf):
    """Die Seiten des PDFs, jede als Liste ihrer nicht leeren Zeilen ohne Seitenzahlen und Aufzählungszeichen."""
    text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, check=True, text=True).stdout
    return [
        [line for line in map(str.strip, page.split("\n")) if line not in NOISE and not re.fullmatch(r"\d{1,3}", line)]
        for page in text.split("\f")
    ]


def kopf_fuss(*fassungen):
    """Die Zeilen, die in den Randzeilen von mindestens drei Seiten aller Fassungen gleich vorkommen."""
    zaehler = Counter(line for seiten in fassungen for seite in seiten for line in set(seite[:RAND] + seite[-RAND:]))
    return {line for line, n in zaehler.items() if n >= 3 and len(line) < 120}


def entsilben(lines):
    """Fügt am Zeilenende getrennte Wörter zusammen und lässt Ergänzungsstriche stehen."""
    result = []
    for line in lines:
        getrennt = result and re.search(r"\w-$", result[-1])
        if getrennt and re.match(r"[a-zäöüß]", line) and line.split(maxsplit=1)[0] not in BINDEWOERTER:
            result[-1] = result[-1][:-1] + line
        else:
            result.append(line)
    return result


def sentences(seiten, rand):
    """Die Sätze einer Fassung ohne die Kopf- und Fußzeilen `rand`."""
    lines = [
        line
        for seite in seiten
        for i, line in enumerate(seite)
        if not (line in rand and (i < RAND or i >= len(seite) - RAND))
    ]
    text = re.sub(r"\s+", " ", " ".join(entsilben(lines)))
    return [s.strip() for s in SENTENCE.split(text) if s.strip()]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    alt, neu = pages(sys.argv[1]), pages(sys.argv[2])
    rand = kopf_fuss(alt, neu)
    alt, neu = sentences(alt, rand), sentences(neu, rand)
    matcher = difflib.SequenceMatcher(None, alt, neu, autojunk=False)
    stellen = 0
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        stellen += 1
        print(f"=== {op} alt[{i1}:{i2}] neu[{j1}:{j2}]")
        for s in alt[i1:i2]:
            print("  - " + s)
        for s in neu[j1:j2]:
            print("  + " + s)
    print(f"vertragsvergleich: {stellen} geänderte Stelle(n)", file=sys.stderr)


if __name__ == "__main__":
    main()
