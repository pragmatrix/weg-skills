#!/bin/sh
# Installs the WEG skills into one project. Each skill becomes a symlink under the project's `.claude/skills/`, and
# each link gets its own line in the project's `.gitignore`, because the link points into this clone on this machine.
# Skills the project keeps in `.claude/skills/` itself stay untouched. Running the script again refreshes the links.
#
# Usage: install.sh PROJECT [SKILL...]
# Without SKILL, every skill of this repository is installed.
set -eu

repo=$(cd "$(dirname "$0")" && pwd -P)
if [ $# -lt 1 ]; then
    echo "usage: $0 PROJECT [SKILL...]" >&2
    exit 2
fi
project=$(cd "$1" && pwd -P)
shift
if [ $# -eq 0 ]; then
    set -- $(cd "$repo" && for f in */SKILL.md; do dirname "$f"; done)
fi

ignore="$project/.gitignore"
# An entry appended to a file without a final newline would merge with its last line.
if [ -s "$ignore" ] && [ -n "$(tail -c 1 "$ignore")" ]; then
    echo >> "$ignore"
fi

mkdir -p "$project/.claude/skills"
for skill; do
    if [ ! -f "$repo/$skill/SKILL.md" ]; then
        echo "install.sh: $repo has no skill $skill" >&2
        exit 1
    fi
    link="$project/.claude/skills/$skill"
    if [ -e "$link" ] && [ ! -L "$link" ]; then
        echo "install.sh: $link is a folder of the project, not a link, and stays as it is" >&2
        exit 1
    fi
    ln -sfn "$repo/$skill" "$link"
    entry="/.claude/skills/$skill"
    grep -qxF "$entry" "$ignore" 2>/dev/null || echo "$entry" >> "$ignore"
    echo "$skill → $link"
done
