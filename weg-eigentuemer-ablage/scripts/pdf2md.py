#!/usr/bin/env python3
"""Legt neben jedem PDF eine Markdown-Datei mit dem extrahierten Text an.

Aufruf (im Projektordner, siehe `projekt.py`):
    python3 pdf2md.py            fehlende und veraltete MDs erzeugen
    python3 pdf2md.py --check    nur melden, Exit-Code 1 wenn eine MD fehlt, veraltet oder verwaist ist
    python3 pdf2md.py --prune    zusätzlich verwaiste MDs löschen (PDF umbenannt/gelöscht)
    python3 pdf2md.py --force    alle generierten MDs neu erzeugen
    python3 pdf2md.py --quiet    nur Änderungen ausgeben, kombinierbar mit den anderen Optionen

`X.pdf` ergibt `X.md` im selben Ordner. Die Endung `.pdf` zählt in jeder Schreibweise, auch `.PDF`. Ausgenommen sind
die Ordner außerhalb der Ablage (`projekt.skipped`) und PDFs, die auf ein Muster in `scripts/pdf2md-ignore.txt`
passen. Die MDs ausgenommener PDFs gelten als verwaist und werden mit --prune gelöscht.

Erzeugte Dateien tragen in der ersten Zeile eine Markierung. Nur sie werden überschrieben. Von Hand angelegte MDs
gleichen Namens bleiben unberührt. Die Markierung nennt den SHA-256-Hash des PDFs, aus dem die MD erzeugt wurde. Eine
MD gilt als veraltet, wenn dieser Hash nicht zum PDF passt oder fehlt. Dateizeiten zählen nicht, weil `git clone` und
`git worktree add` sie neu setzen.

Benötigt Poppler (`pdftotext`, `pdfinfo`, `pdftoppm`). Fehlt Poppler, bricht das Skript mit Exit-Code 1 ab. Ein PDF,
dessen Seitenzahl `pdfinfo` nicht lesen kann, bekommt keine MD und wird als Fehler gemeldet. Für Scans ohne Textebene
wird, falls vorhanden, Tesseract für OCR verwendet (bevorzugt Sprache `deu`, sonst `eng`).
"""
from pathlib import Path
import argparse
import fnmatch
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile

from projekt import ROOT, ignore_patterns, nfc, skipped

# Jede erzeugte MD beginnt in Zeile 1 mit `MARKER`. Der Anfang nennt den früheren Ort dieses Skripts und bleibt so,
# damit auch ältere MDs als erzeugt erkannt werden. Hinter ihm steht der Hash des PDFs in der Form `sha256=<hex>`.
MARKER = "<!-- generiert von scripts/pdf2md.py"
HASH = re.compile(r"\bsha256=([0-9a-f]{64})\b")
MIN_CHARS_PER_PAGE = 20  # darunter gilt eine Seite als Scan ohne Textebene
MAX_OCR_PAGES = 10  # längere Scans (z. B. handschriftliche Statik) nicht per OCR lesen


def pdfs(patterns):
    for p in sorted(ROOT.rglob("*.[pP][dD][fF]")):
        rel = p.relative_to(ROOT)
        if skipped(rel) or any(fnmatch.fnmatch(nfc(rel.as_posix()), pat) for pat in patterns):
            continue
        yield p


def marker(md):
    """Erste Zeile einer erzeugten MD, oder None für eine von Hand angelegte oder unlesbare Datei."""
    try:
        with md.open(encoding="utf-8") as f:
            line = f.readline()
    except (OSError, UnicodeDecodeError):
        return None
    return line if line.startswith(MARKER) else None


def is_generated(md):
    return marker(md) is not None


def pdf_hash(pdf):
    with pdf.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def state(md, digest):
    """Zustand der MD zum PDF mit dem Hash `digest`: "fehlt", "veraltet", "aktuell" oder "von Hand"."""
    if not md.exists():
        return "fehlt"
    line = marker(md)
    if line is None:
        return "von Hand"
    m = HASH.search(line)
    return "aktuell" if m and m.group(1) == digest else "veraltet"


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout


def page_count(pdf):
    for line in run("pdfinfo", str(pdf)).splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def ocr_lang():
    if not shutil.which("tesseract"):
        return None
    langs = run("tesseract", "--list-langs").split()
    return "deu" if "deu" in langs else ("eng" if "eng" in langs else None)


def ocr_page(pdf, n, lang):
    with tempfile.TemporaryDirectory() as d:
        base = Path(d) / "p"
        subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", "-f", str(n), "-l", str(n), "-singlefile",
                        str(pdf), str(base)], check=False, capture_output=True)
        img = base.with_suffix(".png")
        if not img.exists():
            return ""
        return run("tesseract", str(img), "-", "-l", lang, "--psm", "3")


def convert(pdf, digest, pages, lang):
    rel = pdf.relative_to(ROOT).as_posix()
    out = [f"{MARKER} aus {pdf.name} (sha256={digest}); nicht von Hand bearbeiten, neu erzeugen mit `just md` -->",
           "", f"# {pdf.stem}", "", f"Quelle: `{rel}`, {pages} Seite(n).", ""]
    notes = set()
    ocr_left = MAX_OCR_PAGES
    for n in range(1, pages + 1):
        text = run("pdftotext", "-layout", "-enc", "UTF-8", "-f", str(n), "-l", str(n), str(pdf), "-")
        if len("".join(text.split())) < MIN_CHARS_PER_PAGE:
            if lang and ocr_left > 0:
                ocr_left -= 1
                text = ocr_page(pdf, n, lang)
                notes.add(f"Seiten ohne Textebene per OCR ({lang}) gelesen, Fehler möglich.")
            elif lang:
                text = ""
                notes.add(f"Nur die ersten {MAX_OCR_PAGES} Seiten ohne Textebene per OCR gelesen; Rest im PDF ansehen.")
            else:
                text = ""
                notes.add("Seiten ohne Textebene; kein OCR verfügbar (Tesseract installieren).")
        text = "\n".join(line.rstrip() for line in text.replace("\f", "").splitlines()).strip("\n")
        out += [f"## Seite {n}", ""]
        out += (["```text", text, "```"] if text.strip() else ["_(kein Text erkannt)_"]) + [""]
    if notes:
        out[5:5] = [f"> {n}" for n in sorted(notes)] + [""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="nur Änderungen ausgeben")
    a = ap.parse_args()

    missing = [tool for tool in ("pdftotext", "pdfinfo") if not shutil.which(tool)]
    if missing:
        print(f"pdf2md: Poppler fehlt, es gibt kein {' und '.join(missing)} (brew install poppler)", file=sys.stderr)
        return 1
    lang = ocr_lang()
    todo, manual, unreadable = [], [], []
    wanted = {pdf.with_suffix(".md"): pdf for pdf in pdfs(ignore_patterns("pdf2md-ignore.txt"))}
    for md, pdf in sorted(wanted.items()):
        digest = pdf_hash(pdf)
        status = state(md, digest)
        if status == "von Hand":
            manual.append(md)
        elif a.force or status != "aktuell":
            todo.append((pdf, md, digest, status))

    # Eine erzeugte MD ist verwaist, wenn ihr PDF gelöscht, umbenannt oder per pdf2md-ignore.txt ausgenommen ist.
    orphans = [md for md in ROOT.rglob("*.md")
               if not skipped(md.relative_to(ROOT)) and is_generated(md) and md not in wanted]

    for pdf, md, digest, status in todo:
        if a.check:
            print(f"{status}: {md.relative_to(ROOT)}")
        elif pages := page_count(pdf):
            md.write_text(convert(pdf, digest, pages, lang), encoding="utf-8")
            print(f"erzeugt: {md.relative_to(ROOT)}")
        else:
            unreadable.append(pdf)
            print(f"nicht lesbar (pdfinfo nennt keine Seiten): {pdf.relative_to(ROOT)}", file=sys.stderr)
    for md in orphans:
        print(f"{'gelöscht' if a.prune and not a.check else 'verwaist'}: {md.relative_to(ROOT)}")
        if a.prune and not a.check:
            md.unlink()
    if not a.quiet:
        for md in manual:
            print(f"übersprungen (nicht generiert): {md.relative_to(ROOT)}")
        if not todo and not orphans:
            print("pdf2md: alles aktuell")
    return 1 if unreadable or (a.check and (todo or orphans)) else 0


if __name__ == "__main__":
    sys.exit(main())
