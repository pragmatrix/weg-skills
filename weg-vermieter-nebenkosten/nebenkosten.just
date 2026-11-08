# Rezepte des Skills weg-vermieter-nebenkosten. Die justfile des Projekts bindet sie ein mit
#   import '.claude/skills/weg-vermieter-nebenkosten/nebenkosten.just'
# Sie laufen im Projektordner und brauchen typst, python3 und pdfunite aus Poppler.

# Nebenkostenabrechnung des Jahres aus der Datenbasis in Vermietung/JAHR/ prüfen und als PDF mit Anlagen nach tmp/ bauen
[positional-arguments]
nebenkosten jahr:
    #!/usr/bin/env bash
    set -euo pipefail
    shopt -s nullglob
    dateien=("Vermietung/$1"/nebenkostenabrechnung_"$1"_*.json)
    if [ "${#dateien[@]}" -ne 1 ]; then
      echo "ABBRUCH: In Vermietung/$1 passen ${#dateien[@]} Dateien auf nebenkostenabrechnung_$1_*.json, erwartet ist genau eine." >&2
      exit 1
    fi
    # Die Anlagen stehen in der Datenbasis unter anlagen[].datei, als Pfad relativ zum Projektordner.
    anlagen=()
    while IFS= read -r -d '' a; do anlagen+=("$a"); done < <(python3 -c '
    import json, sys
    for a in json.load(open(sys.argv[1], encoding="utf-8")).get("anlagen", []):
        if isinstance(a, dict) and isinstance(a.get("datei"), str):
            print(a["datei"], end="\0")
    ' "${dateien[0]}")
    for a in ${anlagen[@]+"${anlagen[@]}"}; do
      [ -f "$a" ] || { echo "ABBRUCH: Die Anlage $a fehlt." >&2; exit 1; }
    done
    mkdir -p tmp
    ziel="tmp/Nebenkostenabrechnung $1.pdf"
    arbeit=$(mktemp -d "${TMPDIR:-/tmp}/nebenkosten.XXXXXX")
    trap 'rm -rf "$arbeit"' EXIT
    typst compile --input daten="$(cat "${dateien[0]}")" "{{source_directory()}}/nebenkostenabrechnung.typ" "$arbeit/brief.pdf"
    if [ "${#anlagen[@]}" -gt 0 ]; then
      pdfunite "$arbeit/brief.pdf" "${anlagen[@]}" "$ziel"
    else
      cp "$arbeit/brief.pdf" "$ziel"
    fi
    echo "$ziel"
