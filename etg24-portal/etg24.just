# Rezepte des Skills etg24-portal. Die justfile des Projekts bindet sie ein mit
#   import '~/.claude/skills/etg24-portal/etg24.just'

# Direktlink ins ETG24-Portal zu einer Datei der Ablage ausgeben (aus der Spalte Portal der Abgleichliste)
[positional-arguments]
etg24-link +dateien:
    python3 "{{source_directory()}}/etg24_link.py" "$@"

# Direktlink ins ETG24-Portal zu einer Datei der Ablage im Browser öffnen
[positional-arguments]
etg24-open +dateien:
    python3 "{{source_directory()}}/etg24_link.py" --open "$@"

# Empfänger für Downloads aus dem ETG24-Portal starten (siehe Skill etg24-portal)
etg24-recv ziel:
    python3 -I "{{source_directory()}}/etg24_recv.py" "{{ziel}}"
