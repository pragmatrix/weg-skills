# Rezepte des Skills weg-abrechnung-pruefen. Die justfile des Projekts bindet sie ein mit
#   import '~/.claude/skills/weg-abrechnung-pruefen/pruefen.just'

# Zwei Fassungen eines Vertrags Satz für Satz vergleichen (Ausgabe nach tmp/ umleiten)
vergleich alt neu:
    python3 "{{source_directory()}}/vertragsvergleich.py" "{{alt}}" "{{neu}}"
