#!/usr/bin/env python3
"""Legt neben jedem PDF eine Markdown-Datei mit dem extrahierten Text an.

Aufruf (im Projektordner, siehe `projekt.py`):
    python3 pdf2md.py            fehlende und veraltete MDs erzeugen
    python3 pdf2md.py --check    nur melden, Exit-Code 1 wenn etwas fehlt
    python3 pdf2md.py --prune    zusätzlich verwaiste MDs löschen (PDF umbenannt/gelöscht)
    python3 pdf2md.py --force    alle generierten MDs neu erzeugen

`X.pdf` ergibt `X.md` im selben Ordner. Ausgenommen sind PDFs, die auf ein Muster in
`scripts/pdf2md-ignore.txt` passen; deren MDs gelten als verwaist und werden mit --prune gelöscht. Erzeugte Dateien tragen in der ersten Zeile eine Markierung und werden
nur dann überschrieben; von Hand angelegte MDs gleichen Namens bleiben unberührt. Eine MD gilt als veraltet, wenn
das PDF neuer ist.

Benötigt Poppler (`pdftotext`, `pdfinfo`, `pdftoppm`). Für Scans ohne Textebene wird, falls vorhanden, Tesseract
für OCR verwendet (bevorzugt Sprache `deu`, sonst `eng`).
"""
from pathlib import Path
import argparse
import fnmatch
import shutil
import subprocess
import sys
import tempfile

from projekt import ROOT

# Die Markierung nennt den früheren Ort dieses Skripts. Sie bleibt so, weil jede erzeugte MD sie in Zeile 1 trägt.
MARKER = "<!-- generiert von scripts/pdf2md.py"
SKIP_DIRS = {"tmp", "scripts", ".claude", ".git"}
MIN_CHARS_PER_PAGE = 20  # darunter gilt eine Seite als Scan ohne Textebene
IGNORE_FILE = ROOT / "scripts" / "pdf2md-ignore.txt"
MAX_OCR_PAGES = 10  # längere Scans (z. B. handschriftliche Statik) nicht per OCR lesen


def ignore_patterns():
    if not IGNORE_FILE.exists():
        return []
    lines = (l.strip() for l in IGNORE_FILE.read_text(encoding="utf-8").splitlines())
    return [l for l in lines if l and not l.startswith("#")]


def pdfs(patterns):
    for p in sorted(ROOT.rglob("*.pdf")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if any(fnmatch.fnmatch(rel.as_posix(), pat) for pat in patterns):
            continue
        yield p


def is_generated(md):
    try:
        with md.open(encoding="utf-8") as f:
            return f.readline().startswith(MARKER)
    except OSError:
        return False


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


def convert(pdf, lang):
    pages = page_count(pdf)
    rel = pdf.relative_to(ROOT).as_posix()
    out = [f"{MARKER} aus {pdf.name}; nicht von Hand bearbeiten, neu erzeugen mit `just md` -->",
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

    if not shutil.which("pdftotext"):
        print("pdf2md: pdftotext fehlt (brew install poppler) – übersprungen", file=sys.stderr)
        return 0
    lang = ocr_lang()
    todo, skipped = [], []
    wanted = set(pdfs(ignore_patterns()))
    for pdf in sorted(wanted):
        md = pdf.with_suffix(".md")
        if md.exists() and not is_generated(md):
            skipped.append(md)
        elif a.force or not md.exists() or md.stat().st_mtime < pdf.stat().st_mtime:
            todo.append((pdf, md))

    # verwaist: PDF gelöscht/umbenannt oder per pdf2md-ignore.txt ausgeschlossen
    orphans = [md for md in ROOT.rglob("*.md") if is_generated(md) and md.with_suffix(".pdf") not in wanted]

    for pdf, md in todo:
        print(f"{'fehlt' if a.check else 'erzeugt'}: {md.relative_to(ROOT)}")
        if not a.check:
            md.write_text(convert(pdf, lang), encoding="utf-8")
    for md in orphans:
        print(f"{'gelöscht' if a.prune and not a.check else 'verwaist'}: {md.relative_to(ROOT)}")
        if a.prune and not a.check:
            md.unlink()
    if not a.quiet:
        for md in skipped:
            print(f"übersprungen (nicht generiert): {md.relative_to(ROOT)}")
        if not todo and not orphans:
            print("pdf2md: alles aktuell")
    return 1 if a.check and (todo or orphans) else 0


if __name__ == "__main__":
    sys.exit(main())
