# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf"]
# ///
"""Annotates the passages of a PDF that an audit report (a Markdown file of one's own) finds fault with, in a copy.

Usage (from the project folder):
    uv run pdf_annotate.py MARKS.toml    (`just annotate MARKS.toml`)

The TOML file names the original (`pdf`), the audit report (`report`), and the output (`output`), each relative to the
folder of the TOML file. `title` names the report in the legend. `legend` gives the page and the rectangle in points
for the legend, for example `legend = { page = 1, rect = [185, 514, 560, 570] }`, on an empty area of the page.
`sections` maps the section numbers of the report to short names for the note, for example
`sections = { 1 = "Ergebnis", 2 = "Fehler", 4 = "Änderungswunsch" }`. Only items from these sections count.

Each `[[mark]]` names the page, the passage, and the report items the passage belongs to (for example
`items = ["2.1", "4.1"]`).

The comparison with an earlier version is optional. When the TOML file names that version (`previous`, for example
"Fassung 10/2024"), every mark needs the change against the earlier version in its own words (`change`, "Unverändert."
for an unchanged passage). `underline` then lists the words of the passage that changed in substance. Without
`previous`, both keys are left out.

A passage starts at `text`. When it spans several lines, `end` names its end. `text` and `end` must each lie within one
line of the PDF. When one occurs several times on the page, `match` and `end_match` (counting from 1) select the
occurrence, or `in` names a line in which `text` is searched. An entry in `underline` is either just a `text` or a table
with the same keys as a passage.

A report item is a list entry that starts with its number (`- 2.1 **Title** Text`). Its indented lines belong to it. An
item can also be a table row as the statement audits use (`| 1.4b | Check | Status | Finding | Evidence |`). The script
copies the text of each item into the note of the annotation. The colour follows the item's weight in the report. Red
marks an item under a heading "Wichtig" or with the status "Abweichung". Blue marks an item from the section named
"Fehler". Yellow marks everything else. With several items, the strongest colour wins.

Each passage is highlighted and carries the note as a comment. In a comparison the note starts with the change against
the earlier version, and the changed words are underlined. The item numbers stand in the right margin so that they show
in a printout too. A legend is added. The original stays unchanged. When the script finds a text not at all or not
exactly once, it stops.
"""
import re
import sys
import tomllib
from pathlib import Path

import pymupdf

# `mdtext.py` belongs to the skill `weg-eigentuemer-ablage`, which is installed next to this skill.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "weg-eigentuemer-ablage" / "scripts"))
from mdtext import plain  # noqa: E402

# The labels and the legend appear in the annotated PDF, whose readers read German.
COLOUR = {"important": (1.0, 0.88, 0.88), "error": (0.9, 0.95, 1.0), "note": (1.0, 0.97, 0.72)}
RANK = ["note", "error", "important"]
MEANING = {
    "important": "Rot: wichtig",
    "error": "Blau: Fehler im Text",
    "note": "Gelb: weitere Auffälligkeit oder nachrangig",
}
UNDERLINE = (0.8, 0.15, 0.0)
# Bullets in front of list entries do not belong to the annotated passage.
BULLETS = {"-", "–", "•"}
ITEM = re.compile(r"- (\d)\.(\d+[a-z]?) (.*)")
TABLE_ITEM = re.compile(r"\| (\d)\.(\d+[a-z]?) \| (.*) \|$")
# Bold markers and the brackets around link texts (after `plain`) would clutter the note.
WITHOUT_MARKDOWN = str.maketrans("", "", "*[]")


def report_items(md, sections):
    """Reads the numbered items of the report from the given sections: number → (weight, note text)."""
    result = {}
    section = weight = number = None
    for line in plain(md).translate(WITHOUT_MARKDOWN).split("\n"):
        if line.startswith("## "):
            section = line[3:4]
            weight = number = None
        elif line.startswith("### "):
            weight = line[4:].strip()
            number = None
        elif (m := ITEM.match(line)) and m[1] in sections:
            number = f"{m[1]}.{m[2]}"
            if weight == "Wichtig":
                kind = "important"
            elif sections[m[1]] == "Fehler":
                kind = "error"
            else:
                kind = "note"
            result[number] = [kind, f"{sections[m[1]]} {number}: {m[3].strip()}"]
        elif (m := TABLE_ITEM.match(line)) and m[1] in sections:
            number = f"{m[1]}.{m[2]}"
            check, status, finding, evidence = (cell.strip() for cell in m[3].split(" | "))
            kind = "important" if status == "Abweichung" else "note"
            text = f"{sections[m[1]]} {number}: {check} ({status}). {finding} Beleg: {evidence}"
            result[number] = [kind, text]
            number = None
        elif number and line.startswith("  ") and line.strip():
            result[number][1] += ("\n" if line.strip().startswith("- ") else " ") + line.strip()
        else:
            number = None
    return result


def fits(words, i, parts):
    """Whether the words from index `i` on contain the parts of the searched text within one line.

    The text may start and end in the middle of a word, for example at the rest of a hyphenated word. The first part
    therefore only needs to be the end of its word, and the last part only the start of its word. A text of a single
    part may lie anywhere inside a word.
    """
    if i + len(parts) > len(words):
        return False
    candidates = words[i : i + len(parts)]
    if any(abs(w[3] - candidates[0][3]) > 2 for w in candidates):
        return False
    if len(parts) == 1:
        return parts[0] in candidates[0][4]
    first, *middle, last = (w[4] for w in candidates)
    return first.endswith(parts[0]) and middle == parts[1:-1] and last.startswith(parts[-1])


def locate(page, words, text, match, frame=None):
    """Indices of the first and last word of the searched text, optionally only within `frame`."""
    parts = text.split()
    matches = [
        (i, i + len(parts) - 1)
        for i in range(len(words))
        if fits(words, i, parts) and (frame is None or frame[0] <= i <= frame[1])
    ]
    if match and match <= len(matches):
        return matches[match - 1]
    if not match and len(matches) == 1:
        return matches[0]
    raise SystemExit(f"p. {page.number + 1}: \"{text}\" found {len(matches)} times within one line")


def lines(page, words, start, stop):
    """The lines of the passage from word `start` to word `stop`, one rectangle per line.

    The passage covers the words in between in the order in which they are stored in the PDF. With two columns (basic
    services on the left, special services on the right) only words from the passage's column count. The passage lies
    in one column when its first text block is narrower than half the page and its start and end lie on the same half
    of the page.
    """
    middle = page.rect.width / 2
    blocks = {b[5]: pymupdf.Rect(b[:4]) for b in page.get_text("blocks")}
    right = words[start][0] >= middle
    # A table row spans the middle, but its label often stands in a narrow block.
    in_column = blocks[words[start][5]].width < middle and (words[stop][2] >= middle) == right
    result = {}
    for x0, y0, x1, y1, word, block, line, _ in words[start : stop + 1]:
        if word in BULLETS or in_column and ((x0 + x1) / 2 >= middle) != right:
            continue
        rect = pymupdf.Rect(x0, y0, x1, y1)
        result[block, line] = result[block, line] | rect if (block, line) in result else rect
    return list(result.values())


def reading_order(words):
    """The words line by line from top to bottom, and within each line from left to right.

    The storage order of the PDF does not serve here, because tables are often stored column by column. Words belong
    to one line when their vertical centres lie at most 3 points apart.
    """
    rows = []
    for word in sorted(words, key=lambda w: (w[1] + w[3]) / 2):
        centre = (word[1] + word[3]) / 2
        if rows and centre - rows[-1][0] <= 3:
            rows[-1][1].append(word)
        else:
            rows.append((centre, [word]))
    return [word for _, row in rows for word in sorted(row, key=lambda w: w[0])]


def passage(page, words, entry):
    """Top edge and lines of a passage from `text` and optionally `end`, `match`, `end_match`, and `in`."""
    if isinstance(entry, str):
        entry = {"text": entry}
    frame = locate(page, words, entry["in"], None) if "in" in entry else None
    start, stop = locate(page, words, entry["text"], entry.get("match"), frame)
    if "end" in entry:
        stop = locate(page, words, entry["end"], entry.get("end_match"))[1]
        if stop < start:
            raise SystemExit(f"p. {page.number + 1}: \"{entry['end']}\" comes before \"{entry['text']}\"")
    return words[start][1], lines(page, words, start, stop)


def annotate(toml_path):
    folder = toml_path.parent
    marks = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    sections = {str(n): name for n, name in marks["sections"].items()}
    items = report_items((folder / marks["report"]).read_text(encoding="utf-8"), sections)
    previous = marks.get("previous")
    doc = pymupdf.open(folder / marks["pdf"])
    # The words come from the unchanged PDF. Otherwise the text of labels already placed would count too.
    original = pymupdf.open(folder / marks["pdf"])
    words = [reading_order(page.get_text("words")) for page in original]
    used = set()
    colours = set()
    # Bottom edge of the last label per page, so that labels of passages close together do not overlap
    occupied = {}
    for mark in marks["mark"]:
        page = doc[mark["page"] - 1]
        top, rects = passage(page, words[page.number], mark)
        if bool(previous) != ("change" in mark) or not previous and "underline" in mark:
            raise SystemExit(f"p. {mark['page']}: \"{mark['text']}\": `change` and `underline` only with `previous`")
        change = [f"Änderung gegenüber {previous}: {mark['change']}"] if previous else []
        missing = [n for n in mark["items"] if n not in items]
        if missing:
            raise SystemExit(f"Item {', '.join(missing)} is not in the report")
        used.update(mark["items"])
        kind = max((items[n][0] for n in mark["items"]), key=RANK.index)
        colours.add(kind)
        note = "\n\n".join(change + [items[n][1] for n in mark["items"]])
        numbers = "·".join(mark["items"])

        highlight = page.add_highlight_annot(rects)
        highlight.set_colors(stroke=COLOUR[kind])
        highlight.set_info(title=f"Prüfung {numbers}", content=note)
        highlight.update()

        for entry in mark.get("underline", []):
            stroke = page.add_underline_annot(passage(page, words[page.number], entry)[1])
            stroke.set_colors(stroke=UNDERLINE)
            stroke.set_info(title=f"Geändert gegenüber {previous}", content=change[0])
            stroke.update()

        top = max(top, occupied.get(page.number, 0) + 1)
        # When the first line reaches into the margin, the label moves to the right. In tables a line consists of
        # several rectangles, one per cell.
        line_end = max(r.x1 for r in rects if r.y0 < rects[0].y1)
        left = max(page.rect.width - 50, line_end + 2)
        margin = pymupdf.Rect(left, top, min(left + 44, page.rect.width - 2), top + 9)
        occupied[page.number] = margin.y1
        label = page.add_freetext_annot(margin, numbers, fontsize=6, text_color=(0, 0, 0), fill_color=COLOUR[kind])
        label.set_info(title=f"Prüfung {numbers}")
        label.update()

    legend(doc, marks, colours)
    unmarked = sorted(set(items) - used, key=lambda n: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", n)])
    if unmarked:
        print(f"Items without a mark: {', '.join(unmarked)}")
    output = folder / marks["output"]
    doc.save(output, garbage=3, deflate=True)
    print(f"{len(marks['mark'])} marks → {output}")


def legend(doc, marks, colours):
    rows = [
        f"Markiert nach der {marks['title']}.",
        f"{len(marks['mark'])} Stellen. Nummern am Rand = Punkte der Prüfung. Die Notiz nennt "
        + ("Änderung und Prüfpunkt." if "previous" in marks else "den Prüfpunkt."),
        " · ".join(MEANING[kind] for kind in reversed(RANK) if kind in colours),
    ]
    if "previous" in marks:
        rows.append(f"Unterstrichen: gegenüber der {marks['previous']} wesentlich geändert")
    page = doc[marks["legend"]["page"] - 1]
    box = pymupdf.Rect(marks["legend"]["rect"])
    field = page.add_freetext_annot(box, "\n".join(rows), fontsize=8, text_color=(0, 0, 0), fill_color=(1, 1, 0.85))
    field.update()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    annotate(Path(sys.argv[1]))
