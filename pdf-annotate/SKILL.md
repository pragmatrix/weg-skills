---
name: pdf-annotate
description: Annotate an audit report's items in a copy of the audited PDF, optionally with the change against an earlier version as note and underline. For an annotated PDF of an audit or a contract comparison.
---

# Annotate audit items in a PDF

An **annotated PDF** is a copy of the audited PDF. Every passage that an audit report finds fault with is highlighted
in colour. It carries the text of the report item as a note and its number in the right margin. In a **comparison**
with an earlier version, the note starts with the change, and the changed words are underlined. The original stays
unchanged.

`pdf_annotate.py` next to this file produces the annotated PDF from a **mark list**. That is a TOML file next to the
audit report with one mark per passage. The layout and keys of the mark list are in the script's docstring.
`uv run pdf_annotate.py` in this skill's folder prints it when called without an argument. When the project already
has mark lists (`*_Markierungen.toml`), take one as a template, for a comparison one with `previous`.

The script is called with `just annotate`. The project's `justfile` imports the recipe with
`import '.claude/skills/pdf-annotate/annotate.just'`. When the import is missing, add it. The skill
`weg-eigentuemer-ablage` sets up a new project (section Neues Projekt einrichten). This skill needs `uv`, `mutool`, and
`magick`, as well as the skills `weg-eigentuemer-ablage` (text MDs, plain text without links) and
`weg-abrechnung-pruefen` (`just vergleich`), installed in the same folder as this skill.

The audit report is the only source of the note texts. When a note should read differently, change the report and
regenerate the PDF. The reports, the PDFs, and their readers are German, so the values in the mark list (`change`,
`title`, `sections`, `previous`) are German too.

## Steps

1. **Read the audit report.** The script takes items that start as a list entry with a number
   (`- 2.1 **Titel** Text`), together with their indented continuation lines. It also takes the table rows of the
   statement audits (`| 1.4b | Prüfpunkt | Status | Befund | Beleg |`). Items under a heading `### Wichtig` or with
   the status "Abweichung" turn red, items from the section that the mark list names "Fehler" turn blue, and all
   others turn yellow. The step is done when you know which sections contain items with a passage in the PDF.
2. **Create the mark list.** Name: `<report without .md>_Markierungen.toml` next to the report. Output:
   `<name of the PDF> markiert.pdf` next to the PDF. For this ending `just md` produces no text MD, because
   `scripts/pdf2md-ignore.txt` in the project lists the pattern `*markiert.pdf`. When it is missing there, add it.
   - Every passage that an item finds fault with gets a mark. When an item concerns several passages, it gets several
     marks. `items` lists the matching change request next to the result.
   - Take the **anchors** `text` and `end` from the text MD of the PDF (`X.pdf` → `X.md`). Each of its lines is a line
     of the PDF. With two columns, each column is a separate piece in the same line. An anchor lies entirely within one
     line. When it ends with a hyphenated word, leave out the hyphen ("Koordi" instead of "Koordi-"). At the start of a
     line it may begin with the rest of a hyphenated word ("barung getroffen").

   The step is done when every wanted item has a mark or no passage of its own in the PDF, for example because it only
   sums up other items. When the user wants only the essential items, take those from the summary (Kurzfazit) and name
   the selection in the header of the mark list.
3. **Comparison (optional).** It belongs to the task when the user names an earlier version or the report itself is a
   comparison. Then the mark list gets `previous` and every mark a `change`.
   - `just vergleich OLD.pdf NEW.pdf > tmp/vergleich.txt` lists the changed sentences.
   - `change` briefly quotes the previous wording and names the new one. Write "Unverändert." only after you found the
     passage in the text MD of the earlier version.
   - `underline` names only the words that change the meaning: an amount, a deadline, a condition, a reference
     quantity, a new or swapped word. Underline entirely new clauses at their core. Deleted text appears only in
     `change`.

   The step is done when every mark has a `change` and every changed passage its underline.
4. **Generate.** `just annotate MARKS.toml`. When the script stops at an anchor, the anchor was not found exactly once
   within one line. Select the occurrence with `match` or `in`, or take another anchor. For the legend, find an empty
   area: `mutool draw -r 72 -o tmp/markiert/legende.png PDF PAGE` renders the page so that pixels and points match. At
   the end the script reports the items without a mark. Each of them needs a reason from step 2.
5. **Check the rendering.** `mutool draw -r 90 -o "tmp/markiert/s%d.png" OUTPUT.pdf` renders all pages. Look at every
   page with a mark:
   - The highlight covers exactly the passage and stays in its column.
   - Underlines lie only under the intended words. For short words, check an enlarged crop (`-r 200`, then
     `magick … -crop`).
   - Labels in the margin and the legend cover no text.

   The step is done when every page with a mark has been looked at and every flaw is fixed.
6. **Follow up.** Enter the annotated PDF with one line in the `README.md` of its main folder. Name the mark list
   there. When the audit report changes later, adjust the numbers in `items` and regenerate the PDF.
