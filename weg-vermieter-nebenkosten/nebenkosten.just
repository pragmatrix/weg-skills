# Rezepte des Skills weg-vermieter-nebenkosten. Die justfile des Projekts bindet sie ein mit
#   import '~/.claude/skills/weg-vermieter-nebenkosten/nebenkosten.just'
# Sie laufen im Projektordner. Die Skripte brauchen openpyxl. PYTHON nennt das Python eines venv, das es hat.

nk_python := env("PYTHON", "python3")

# Nebenkostenabrechnung des Jahres aus der Vorjahresabrechnung als Vorlage bauen (Vermietung/JAHR/)
[positional-arguments]
nebenkosten jahr *vorlage:
    "{{nk_python}}" "{{source_directory()}}/build_abrechnung_xlsx.py" "$@"

# Nebenkostenabrechnung gegen Datenbasis und Vorlage prüfen (Exit-Code 1)
[positional-arguments]
nebenkosten-pruefen jahr *vorlage:
    "{{nk_python}}" "{{source_directory()}}/verify_abrechnung_xlsx.py" "$@"
