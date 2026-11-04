# Rezepte des Skills weg-konten-belege. Die justfile des Projekts bindet sie ein mit
#   import '.claude/skills/weg-konten-belege/konten.just'
# Sie laufen im Projektordner und rufen die Skripte neben dieser Datei auf.

# Datenbasis eines Abrechnungsjahres prüfen: Saldo-Ketten, Buchungslisten, Rechnungssummen, Fundstellen (Exit-Code 1)
konten jahr:
    python3 "{{source_directory()}}/pruefe_belege.py" "Abrechnungen/{{jahr}}"

# Zahlungen von Einheit N laut Abrechnung gegen die Kontoauszüge abgleichen (Exit-Code 1 bei Zahlung ohne Bankbeleg)
zahlungen jahr einheit:
    python3 "{{source_directory()}}/korrelation_zahlungen.py" "Abrechnungen/{{jahr}}/weg_abrechnung_{{jahr}}_we{{einheit}}.json" "Abrechnungen/{{jahr}}/konto_{{jahr}}.json"
