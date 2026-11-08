# WEG Skills

Agent skills for owners of a condominium in Germany (a Wohnungseigentümergemeinschaft, WEG): filing the documents of the WEG, auditing the property manager's statements and plans, reconciling bank statements and receipts, and preparing the operating cost statement for a tenant. The skills follow German law (WEG, BetrKV) and work on German documents, so all of them except `pdf-annotate` are written in German.

## Skills

**Invoked by** says who starts a skill: _you_ (as a slash command, e.g. `/weg-abrechnung-pruefen`), the _agent_ (when the task matches the skill's description), or _both_. **Agents** says where a skill works: _any_ agent that reads skill folders, or _Claude Code_ only.

| Skill | Invoked by | Agents | Description |
|---|---|---|---|
| [`weg-eigentuemer-ablage`](./weg-eigentuemer-ablage/) | both | any | Filing and processes for a condominium from the owner's side: folder layout, naming, source links, proceedings, owners' meetings, motions. Sets up a new project and ships the scripts and `just` recipes the other skills build on. |
| [`weg-abrechnung-pruefen`](./weg-abrechnung-pruefen/) | both | any | Audit report on WEG documents: annual statement (whole and per unit), budget plan, implementation of resolutions, new contract versions. |
| [`pdf-annotate`](./pdf-annotate/) | both | any | Annotate an audit report's items in a copy of the audited PDF, optionally with the changes against an earlier version. |
| [`etg24-portal`](./etg24-portal/) | both | Claude Code | Browse and download documents from a property manager's ETG24 portal and reconcile them with the filing, via the Claude in Chrome extension. |
| [`weg-konten-belege`](./weg-konten-belege/) | both | any | Transfer a WEG's account statements and receipts into a checked JSON dataset and reconcile it with the annual statement, including the owner's own Hausgeld payments. |
| [`weg-vermieter-nebenkosten`](./weg-vermieter-nebenkosten/) | both | any | Operating cost statement for the tenant of a rented unit from the WEG documents: apportionability under the BetrKV, CO₂ cost split, advance payments, statement as a PDF letter from a Typst template. |

### Dependencies

The skills use each other by name. Their scripts find each other inside this repository, so a project can install a subset, but each skill needs the skills it depends on:

- `weg-eigentuemer-ablage` ↔ `weg-abrechnung-pruefen`
- `pdf-annotate` → `weg-eigentuemer-ablage`, `weg-abrechnung-pruefen`
- `etg24-portal` → `weg-eigentuemer-ablage`
- `weg-konten-belege` → `weg-eigentuemer-ablage`, `weg-abrechnung-pruefen`
- `weg-vermieter-nebenkosten` → `weg-konten-belege`, `weg-eigentuemer-ablage`

The skills also need command-line tools:

- `just`, `git`, `python3` (3.11 or newer) and Poppler, optionally Tesseract for scans: all skills. The project's `justfile` imports each skill's `.just` file.
- `uv`, `mutool` and `magick`: `pdf-annotate`
- `typst`: `weg-vermieter-nebenkosten`
- the Claude in Chrome extension: `etg24-portal`

## Installation

The skills are installed per project, so they load only in the folder of a WEG and stay out of every other session. Clone the repository anywhere:

```sh
git clone <url of this repository> ~/dev/weg-skills
```

Then install the skills into the project folder of your WEG:

```sh
~/dev/weg-skills/install.sh ~/Documents/WEG-Musterstraße
```

`install.sh` links every skill into the project's `.claude/skills/` and lists each link in the project's `.gitignore`, because the links point into your clone. Name skills after the project folder to install only those. Skills of the project's own stay untouched. Running the script again refreshes the links.

In a new project, ask the agent to set it up next. The section "Neues Projekt einrichten" of `weg-eigentuemer-ablage` creates the folders, the `AGENTS.md`, the `justfile`, and the hooks.

To update, run `git pull` in the clone.

## Tests

The tests in `tests/` run from the repository root with `python3 -m unittest discover -s tests`. Tests that need
`typst` or PyMuPDF are skipped without them, and
`uv run --with pymupdf python -m unittest discover -s tests` runs them all when `typst` is installed.

## License

[MIT](./LICENSE)
