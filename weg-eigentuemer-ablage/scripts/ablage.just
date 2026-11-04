# Rezepte des Skills weg-eigentuemer-ablage. Die justfile des Projekts bindet sie ein mit
#   import '.claude/skills/weg-eigentuemer-ablage/scripts/ablage.just'
# Sie laufen im Projektordner und rufen die Skripte neben dieser Datei auf.

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
plain datei:
    python3 "{{source_directory()}}/mdtext.py" "{{datei}}"

# Wörter melden, die in einer MD gegenüber Git weggefallen sind, etwa nach dem Nachtragen von Quellenlinks (Exit-Code 1)
wortdiff datei rev="HEAD":
    python3 "{{source_directory()}}/wortdiff.py" "{{datei}}" "{{rev}}"

# PDF-Seite zu einem Suchmuster finden, für die Seitenangabe eines Quellenlinks: just seite '6\.318,90' X.pdf
[positional-arguments]
seite muster +dateien:
    python3 "{{source_directory()}}/seite.py" "$@"

# Fakten (Beträge, Prozente, Daten) ohne Quellenlink melden, ohne Argument in neuen und geänderten MDs (nur Hinweis)
[positional-arguments]
unbelegt *dateien:
    python3 "{{source_directory()}}/check_unbelegt.py" "$@"

# Byte-gleiche Dubletten finden: ohne Argument die ganze Ablage (Exit-Code 1), mit Dateien deren Gegenstück
[positional-arguments]
dup *dateien:
    python3 "{{source_directory()}}/find_dupes.py" "$@"

# Alle Prüfungen vor Commit und Push: Text-MDs aktuell, Linkziele vorhanden, Fundstellen passend, keine Dubletten,
# dazu Hinweise auf Fakten ohne Quellenlink in neuen und geänderten MDs
qa: md-check links dup unbelegt
