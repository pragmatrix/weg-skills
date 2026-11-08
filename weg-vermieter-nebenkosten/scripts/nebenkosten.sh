#!/usr/bin/env bash
# Baut die Nebenkostenabrechnung eines Jahres als PDF mit Anlagen. Aufruf im Projektordner: nebenkosten.sh JAHR
#
# Die Datenbasis ist die eine Datei Vermietung/JAHR/nebenkostenabrechnung_JAHR_*.json. Die Vorlage
# nebenkostenabrechnung.typ im Ordner über diesem Skript prüft sie und setzt den Brief. Danach hängt das Skript die
# Anlagen an, die die Vorlage geprüft hat, und schreibt tmp/Nebenkostenabrechnung JAHR.pdf.
set -euo pipefail
shopt -s nullglob

if [ "$#" -ne 1 ]; then
  echo "Aufruf: nebenkosten.sh JAHR" >&2
  exit 2
fi
jahr=$1
vorlage="$(cd "$(dirname "$0")/.." && pwd)/nebenkostenabrechnung.typ"

dateien=("Vermietung/$jahr"/nebenkostenabrechnung_"$jahr"_*.json)
if [ "${#dateien[@]}" -ne 1 ]; then
  echo "ABBRUCH: In Vermietung/$jahr passen ${#dateien[@]} Dateien auf nebenkostenabrechnung_${jahr}_*.json," \
    "erwartet ist genau eine." >&2
  exit 1
fi
# Die Vorlage liest die Datenbasis über ihren absoluten Pfad, deshalb ist / die Wurzel für Typst.
typst_args=(--root / --input "pfad=$PWD/${dateien[0]}")

arbeit=$(mktemp -d "${TMPDIR:-/tmp}/nebenkosten.XXXXXX")
trap 'rm -rf "$arbeit"' EXIT

# Die Übersetzung prüft die Datenbasis und bricht bei einem Befund ab.
typst compile "${typst_args[@]}" "$vorlage" "$arbeit/brief.pdf"

# Die Pfade der Anlagen kommen als JSON-Liste aus der Vorlage. python3 zerlegt sie nur.
liste=$(typst eval "${typst_args[@]}" --in "$vorlage" 'query(<anlagen>).first().value')
anlagen=()
while IFS= read -r -d '' a; do anlagen+=("$a"); done < <(
  python3 -c 'import json, sys
for a in json.load(sys.stdin):
    print(a, end="\0")' <<<"$liste"
)
for a in ${anlagen[@]+"${anlagen[@]}"}; do
  [ -f "$a" ] || { echo "ABBRUCH: Die Anlage $a fehlt." >&2; exit 1; }
done

mkdir -p tmp
ziel="tmp/Nebenkostenabrechnung $jahr.pdf"
if [ "${#anlagen[@]}" -gt 0 ]; then
  pdfunite "$arbeit/brief.pdf" "${anlagen[@]}" "$ziel"
else
  cp "$arbeit/brief.pdf" "$ziel"
fi
echo "$ziel"
