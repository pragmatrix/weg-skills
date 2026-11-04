#!/usr/bin/env python3
"""Vergleicht zwei Fassungen eines Vertrags Satz für Satz und gibt jede geänderte Stelle aus.

Aufruf:
    python3 vertragsvergleich.py ALT.pdf NEU.pdf > tmp/vergleich.txt
    just vergleich ALT.pdf NEU.pdf

Die Text-MDs neben den PDFs taugen dafür nicht. Sie behalten das Layout und mischen bei zweispaltigen Verträgen
(Grundleistungen links, besondere Leistungen rechts) beide Spalten Zeile für Zeile. Das Skript liest den Text deshalb
mit `pdftotext` ohne `-layout`, also Spalte für Spalte in Lesereihenfolge.

Vor dem Vergleich entfernt es Kopf- und Fußzeilen, Seitenzahlen und Silbentrennungen. Kopf- und Fußzeilen sind Zeilen,
die auf mindestens drei Seiten gleich vorkommen. Dann teilt es den Text in Sätze und vergleicht die Satzfolgen.

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


def pages(pdf):
    text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, check=True, text=True).stdout
    return [[line.strip() for line in page.split("\n")] for page in text.split("\f")]


def sentences(pdf):
    seiten = pages(pdf)
    wiederkehrend = Counter(line for seite in seiten for line in set(seite) if line)
    kopf_fuss = {line for line, n in wiederkehrend.items() if n >= 3 and len(line) < 120}
    lines = [
        line
        for seite in seiten
        for line in seite
        if line not in NOISE and line not in kopf_fuss and not re.fullmatch(r"\d{1,3}", line)
    ]
    text = " ".join(lines)
    text = re.sub(r"(\w)- (?=[a-zäöüß])", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in SENTENCE.split(text) if s.strip()]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    alt, neu = sentences(sys.argv[1]), sentences(sys.argv[2])
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
