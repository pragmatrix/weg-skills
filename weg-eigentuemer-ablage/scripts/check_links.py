#!/usr/bin/env python3
"""Prüft, ob jedes Linkziel in den eigenen Markdown-Dateien existiert.

Aufruf (im Projektordner, siehe `projekt.py`):
    python3 check_links.py   Arbeitsordner prüfen (auch der pre-commit-Hook)

Geprüft werden zwei Arten von Verweisen:
- Markdown-Links `[Text](<Pfad>)` und `[Text](Pfad)`. Der Pfad gilt relativ zur Datei, in der der Link steht.
- Pfade in Backticks, die mit einem Hauptordner beginnen, z. B. `Abrechnungen/2025/X.pdf`. Sie gelten relativ zum
  Projektordner. Pfade mit Platzhaltern (`…`, `*`, `<`, `[`, `JJJJ`) sind Muster und werden übersprungen.

Ein Pfad gilt auch dann als vorhanden, wenn er eine Datei in einem ZIP-Archiv des Projekts benennt. Er besteht dann
aus dem Pfad des Archivs und dem Pfad im Archiv, etwa `Verwaltung/Muster/Sicherung.zip/Angebote/Angebot.pdf`. So
bleiben Verweise auf Dateien in einer Sicherung prüfbar, etwa auf die Dokumente einer früheren Verwaltung.

Zu jedem Link auf ein PDF prüft das Skript außerdem die Fundstelle, wenn neben dem PDF eine Text-MD liegt. Das gilt
für Links mit und ohne Tooltip und für die Endung `.pdf` in jeder Schreibweise:
- Die Seite aus dem Linktext oder Tooltip („S. 3“, „S. 4–6“, „S. 1 und 3“) muss es im PDF geben. Ein Bereich
  zählt aufsteigend. „S. 2–1“ ist ein Fehler, auch als Teil einer Angabe wie „S. 2–1 und 3“.
- Jedes Zitat „…“ im Tooltip muss auf einer dieser Seiten stehen. Ein „…“ im Zitat trennt Teilstücke, die einzeln
  gesucht werden. Gesucht wird in der Text-MD und, falls dort das Spaltenlayout den Satz zerreißt, im Text des PDF in
  Lesereihenfolge. Silbentrennung und Zeilenumbrüche zählen nicht. Kurze Stücke unter 12 Zeichen und zitierte
  Abschnittstitel („Abschnitt „…““) werden übersprungen.

Zu jedem Link auf eine eigene MD prüft das Skript die nummerierten Punkte, die Linktext oder Tooltip nennen, etwa
„Nr. 4.4“, „Prüfpunkt 1.8c“ oder „Frage 4.2“. Die Nummer muss im Ziel einen Punkt beginnen: einen Listenpunkt
(`- 4.4`, `- [ ] 6.1`, `1.`), eine Tabellenzeile (`| 1.8c |`) oder eine Überschrift (`## 4.`). So fällt ein Verweis
auf, dessen Nummer sich im Ziel geändert hat. Teilen sich mehrere Links denselben Tooltip, genügt die Nummer in
einem ihrer Ziele. Ein Link ohne Tooltip wird für sich geprüft. Eine „Nr.“ darf auch eine Vertragsnummer sein, die
das Ziel als „Nr. 4.2.2“ zitiert. Die Nummernregel steht im Abschnitt „Gliederung und Gewichtung“ des Skills
`weg-eigentuemer-ablage`.

Ausgenommen sind erzeugte Text-MDs (Markierung von `pdf2md.py`) und Codeblöcke. Ausgenommen sind auch die Ordner
außerhalb der Ablage. Das sind `tmp/`, `Notizen/` und `scripts/` direkt im Projektordner und jeder versteckte Ordner
wie `.git/` oder `.obsidian/` (`projekt.skipped`).
"""
from pathlib import Path, PurePosixPath
import argparse
import os
import re
import subprocess
import sys
import urllib.parse
import zipfile

from projekt import HAUPTORDNER, ROOT, nfc, skipped
from seite import PAGE

# Die Markierung nennt den früheren Ort von `pdf2md.py`. Sie bleibt so, weil jede erzeugte MD sie in Zeile 1 trägt.
MARKER = "<!-- generiert von scripts/pdf2md.py"
TOP_DIRS = (*HAUPTORDNER, "scripts")

FENCE = re.compile(r"^```.*?^```", re.S | re.M)
CODE = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\]\(<([^>]+)>|\]\(([^)\s<>]+)")
PLACEHOLDER = re.compile(r"[…*<\[]|JJJJ")
PDF_LINK = re.compile(r'\[([^\]]+)\]\((?:<([^>]+\.pdf)>|([^)\s<>]+\.pdf))(?:\s+"([^"]*)")?\)', re.I)
SEITEN = re.compile(r"S\. (\d+(?:\s*(?:[–-]|und|,)\s*\d+)*)")
ZITAT = re.compile(r"(Abschnitte? )?„([^“]+)“")
MD_LINK = re.compile(r'\[([^\]]*)\]\((?:<([^>#]+\.md)(?:#[^>]*)?>|([^)\s<>#]+\.md)(?:#[^)\s]*)?)(?:\s+"([^"]*)")?\)')
POINT = re.compile(r"\b(Nr\.|Prüfpunkt|Frage|Befund|Grund|Änderungswunsch|Ergebnis) (\d+(?:\.\d+)*[a-z]?)\b")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


class Worktree:
    """Liest die MDs und prüft Pfade im Arbeitsordner."""

    def markdown_files(self):
        for p in sorted(ROOT.rglob("*.md")):
            rel = p.relative_to(ROOT)
            if not skipped(rel):
                yield rel.as_posix(), p.read_text(encoding="utf-8", errors="replace")

    def exists(self, rel):
        return (ROOT / rel).exists()

    def read(self, rel):
        path = ROOT / rel
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def zip_members():
    """Projektrelative Pfade der Dateien in ZIP-Archiven, jeweils als Pfad des Archivs und Pfad im Archiv."""
    members = set()
    for z in ROOT.rglob("*.zip"):
        archive = z.relative_to(ROOT)
        if not skipped(archive):
            with zipfile.ZipFile(z) as f:
                members.update(nfc(os.path.normpath(archive / n.rstrip("/"))) for n in f.namelist())
    return members


def under_symlink(rel):
    """Liegt das Ziel unter einem Symlink im Projekt, z. B. `Notizen/`?"""
    parts = PurePosixPath(rel).parts
    return any((ROOT.joinpath(*parts[: i + 1])).is_symlink() for i in range(len(parts) - 1))


def blank(match):
    """Ersetzt einen Treffer durch Leerzeichen und behält die Zeilenumbrüche, damit Zeilennummern stimmen."""
    return re.sub(r"[^\n]", " ", match.group(0))


def targets(text, folder):
    """Liefert (Zeilennummer, Pfad, Kandidaten) für jeden Verweis im Text.

    Die Kandidaten sind die projektrelativen Pfade, unter denen das Ziel liegen darf. Ein Link gilt relativ zur Datei.
    Ein Pfad in Backticks gilt relativ zum Projektordner oder, etwa in der `AGENTS.md` eines Vorgangs, zur Datei.
    """
    text = FENCE.sub(blank, text)
    for m in CODE.finditer(text):
        span = m.group(1)
        if span.startswith(tuple(d + "/" for d in TOP_DIRS)) and not PLACEHOLDER.search(span):
            yield text.count("\n", 0, m.start()) + 1, span, [span, str(folder / span)]
    prose = CODE.sub(blank, text)
    for m in LINK.finditer(prose):
        target = urllib.parse.unquote((m.group(1) or m.group(2)).split("#")[0])
        if target and not SCHEME.match(target):
            yield prose.count("\n", 0, m.start()) + 1, target, [str(folder / target)]


def flat(text):
    """Text ohne Silbentrennung, weiche Trennstriche und Zeilenumbrüche, damit Zitate über Zeilen hinweg passen."""
    text = re.sub(r"(\w)-\s+(?=[a-zäöüß])", r"\1", text.replace("\u00ad", ""))
    return re.sub(r"\s+", " ", text).strip()


def page_numbers(spec):
    """Seiten einer Angabe. „4–6“ ergibt 4, 5 und 6. „1 und 3“ ergibt 1 und 3.

    Enthält die Angabe einen absteigenden Bereich, ist sie als Ganzes ungültig, und das Ergebnis ist leer. Sonst
    würde „S. 2–1 und 3“ still nur auf S. 3 suchen.
    """
    numbers = []
    for part in re.split(r"\s*(?:und|,)\s*", spec):
        a, _, b = part.partition("–") if "–" in part else part.partition("-")
        if int(b or a) < int(a):
            return []
        numbers += range(int(a), int(b or a) + 1)
    return numbers


class Pdfs:
    """Seitentexte der PDFs: aus der Text-MD und bei Bedarf aus `pdftotext` in Lesereihenfolge."""

    def __init__(self):
        self.md, self.raw = {}, {}

    def pages(self, pdf):
        if pdf not in self.md:
            pages, current = {}, None
            md = pdf.with_suffix(".md")
            for line in md.read_text(encoding="utf-8").split("\n") if md.exists() else []:
                m = PAGE.match(line)
                if m:
                    current = int(m.group(1))
                    pages[current] = []
                elif current:
                    pages[current].append(line)
            self.md[pdf] = {n: flat("\n".join(lines)) for n, lines in pages.items()}
        return self.md[pdf]

    def reading_order(self, pdf, n):
        if (pdf, n) not in self.raw:
            out = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), str(pdf), "-"], capture_output=True)
            self.raw[pdf, n] = flat(out.stdout.decode("utf-8", errors="replace"))
        return self.raw[pdf, n]


def citation_errors(text, folder, pdfs):
    """Liefert (Zeilennummer, Meldung) für jede Seite und jedes Zitat, das nicht zum verlinkten PDF passt."""
    prose = CODE.sub(blank, FENCE.sub(blank, text))
    for m in PDF_LINK.finditer(prose):
        label, angled, bare, tip = m.groups()
        target, tip = angled or bare, tip or ""
        pdf = ROOT / os.path.normpath(folder / urllib.parse.unquote(target))
        pages = pdfs.pages(pdf)
        spec = SEITEN.search(label) or SEITEN.search(tip)
        if not pages or not spec:
            continue
        line = prose.count("\n", 0, m.start()) + 1
        cited = page_numbers(spec.group(1))
        if not cited or min(cited) < 1:
            yield line, f"S. {spec.group(1)} ist keine gültige Seitenangabe"
            continue
        if max(cited) > max(pages):
            yield line, f"S. {spec.group(1)} gibt es nicht, {target} hat {max(pages)} Seiten"
            continue
        for section, quote in ZITAT.findall(tip):
            for piece in (flat(p) for p in quote.split("…")):
                if section or len(piece) < 12:
                    continue
                if any(piece in pages.get(n, "") or piece in pdfs.reading_order(pdf, n) for n in cited):
                    continue
                yield line, f"Zitat „{piece[:60]}“ steht nicht auf S. {spec.group(1)} von {target}"


def starts_point(number, text):
    """Beginnt im Text ein Listenpunkt, eine Tabellenzeile oder eine Überschrift mit dieser Nummer?"""
    n = re.escape(number)
    return re.search(rf"^\s*(?:[-*] (?:\[[ x]\] )?{n}[\s|]|{n}\.\s|\|\s*{n}\s*\||#+\s+{n}\.?\s)", text, re.M)


def numbering_errors(text, folder, source):
    """Liefert (Zeilennummer, Meldung) für jede Nummer in einem MD-Link, die in keinem passenden Ziel vorkommt."""
    prose = CODE.sub(blank, FENCE.sub(blank, text))
    links = []
    for m in MD_LINK.finditer(prose):
        label, angled, bare, tip = m.groups()
        target = angled or bare
        rel = os.path.normpath(folder / urllib.parse.unquote(target))
        body = None if rel.startswith("..") or under_symlink(rel) else source.read(rel)
        if body is not None and not body.startswith(MARKER):
            links.append((m.start(), label, target, tip or "", body))
    # Links mit demselben Tooltip teilen sich die Nummern. Gemeint ist dann meist nur eines der Ziele.
    bodies = {}
    for _, _, _, tip, body in links:
        bodies.setdefault(tip, []).append(body)
    # Ein Link ohne Tooltip teilt nichts mit anderen. Sein Schlüssel ist deshalb das Linkziel.
    reported = set()
    for start, label, target, tip, body in links:
        for kind, number in dict.fromkeys(POINT.findall(label + " " + tip)):
            pool = bodies[tip] if tip else [body]
            key = ("Tooltip", tip, number) if tip else ("Ziel", target, number)
            clause = re.compile(rf"Nr\. {re.escape(number)}(?![.\d]*\d)") if kind == "Nr." else None
            if key in reported or any(starts_point(number, b) or (clause and clause.search(b)) for b in pool):
                continue
            reported.add(key)
            yield prose.count("\n", 0, start) + 1, f"Punkt {number} gibt es in {target} nicht"


def found(source, rel, members):
    rel = os.path.normpath(rel)
    if rel.startswith("..") or under_symlink(rel):
        return (ROOT / rel).exists()
    return source.exists(rel) or nfc(rel) in members


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    source = Worktree()
    members = zip_members()
    pdfs = Pdfs()
    broken, citations = [], []
    for path, text in source.markdown_files():
        if text.startswith(MARKER):
            continue
        folder = PurePosixPath(path).parent
        for line, target, candidates in targets(text, folder):
            if not any(found(source, rel, members) for rel in candidates):
                broken.append(f"{path}:{line}: {target}")
        citations += [f"{path}:{line}: {msg}" for line, msg in citation_errors(text, folder, pdfs)]
        citations += [f"{path}:{line}: {msg}" for line, msg in numbering_errors(text, folder, source)]

    # Die Zusammenfassung steht vor den Einzelfällen, weil Git-Oberflächen wie VS Code nur die erste Zeile zeigen.
    if broken:
        print(f"check_links: {len(broken)} Linkziel(e) fehlen", file=sys.stderr)
    if citations:
        print(f"check_links: {len(citations)} Fundstelle(n) passen nicht", file=sys.stderr)
    for b in broken + citations:
        print(b)
    if broken or citations:
        sys.exit(1)
    print("check_links: alle Linkziele vorhanden, Fundstellen passen")


if __name__ == "__main__":
    main()
