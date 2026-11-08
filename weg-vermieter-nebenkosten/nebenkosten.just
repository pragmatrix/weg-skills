# Rezepte des Skills weg-vermieter-nebenkosten. Die justfile des Projekts bindet sie ein mit
#   import '.claude/skills/weg-vermieter-nebenkosten/nebenkosten.just'
# Sie laufen im Projektordner und rufen die Skripte in scripts/ neben dieser Datei auf.

# Nebenkostenabrechnung des Jahres aus Vermietung/JAHR/ prüfen und als PDF mit Anlagen nach tmp/ bauen
[positional-arguments]
nebenkosten jahr:
    bash "{{source_directory()}}/scripts/nebenkosten.sh" "$@"
