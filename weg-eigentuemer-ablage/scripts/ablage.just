# Rezepte des Skills weg-eigentuemer-ablage. Die justfile des Projekts bindet sie ein mit
#   import '.claude/skills/weg-eigentuemer-ablage/scripts/ablage.just'
# Sie rufen die Skripte neben dieser Datei auf. Rezepte ohne Datei laufen im Projektordner. Rezepte mit Dateien
# laufen mit [no-cd] im aktuellen Ordner, damit ein relativer Dateiname dort gilt, wo der Nutzer gerade ist.

# Text aus PDFs als Markdown neben das PDF legen (nur fehlende/veraltete)
md:
    python3 "{{source_directory()}}/pdf2md.py"

# Prüfen, ob MDs fehlen oder veraltet sind (Exit-Code 1)
md-check:
    python3 "{{source_directory()}}/pdf2md.py" --check

# Wie md, zusätzlich MDs löschen, deren PDF umbenannt oder gelöscht wurde
md-prune:
    python3 "{{source_directory()}}/pdf2md.py" --prune

# Prüfen, ob jedes Linkziel existiert und Seiten und Zitate zum verlinkten PDF passen (Exit-Code 1)
links:
    python3 "{{source_directory()}}/check_links.py"

# Eine MD ohne Linkziele und Tooltips ausgeben, zum Lesen langer Ausarbeitungen: [Text](<Pfad> "Tooltip") → [Text]
[no-cd]
plain datei:
    python3 "{{source_directory()}}/mdtext.py" "{{datei}}"

# Wörter melden, die in einer MD gegenüber Git weggefallen sind, etwa nach dem Nachtragen von Quellenlinks (Exit-Code 1)
[no-cd]
wortdiff datei rev="HEAD":
    python3 "{{source_directory()}}/wortdiff.py" "{{datei}}" "{{rev}}"

# PDF-Seite zu einem Suchmuster finden, für die Seitenangabe eines Quellenlinks: just seite '6\.318,90' X.pdf
[no-cd]
[positional-arguments]
seite muster +dateien:
    python3 "{{source_directory()}}/seite.py" "$@"

# Fakten (Beträge, Prozente, Daten) ohne Quellenlink melden, ohne Argument in neuen und geänderten MDs (nur Hinweis)
[no-cd]
[positional-arguments]
unbelegt *dateien:
    python3 "{{source_directory()}}/check_unbelegt.py" "$@"

# Byte-gleiche Dubletten finden: ohne Argument die ganze Ablage (Exit-Code 1), mit Dateien deren Gegenstück
[no-cd]
[positional-arguments]
dup *dateien:
    python3 "{{source_directory()}}/find_dupes.py" "$@"

# Alle Prüfungen vor Commit und Push: md-check, links, dup und unbelegt, auch wenn eine davon fehlschlägt (Exit-Code 1)
qa:
    #!/bin/sh
    status=0
    for check in md-check links dup unbelegt; do
        "{{just_executable()}}" --justfile "{{justfile()}}" "$check" || status=1
    done
    exit $status
