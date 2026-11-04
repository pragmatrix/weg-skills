# Recipes of the skill pdf-annotate. The project's justfile imports them with
#   import '.claude/skills/pdf-annotate/annotate.just'

# Annotate the passages an audit finds fault with in a copy of the PDF (marks and paths in the TOML file)
annotate marks:
    uv run -q "{{source_directory()}}/pdf_annotate.py" "{{marks}}"
