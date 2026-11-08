# Agent skills

This repository publishes skills that other people install. Each skill is written for everyone who works within its
scope, not for the person or project that prompted it.

## Write skills for everyone in their scope

- **Scope** is the deliberate restriction of a skill: a domain, a jurisdiction, a language, a platform, or a tool. The
  WEG skills, for example, are limited to German condominium law (WEG, BetrKV) and German documents, and
  `etg24-portal` is limited to property managers that use the ETG24 portal. A skill names its scope in its description
  or its first section.
- Within its scope a skill works for every user. It serves any condominium, any property manager, any repository, and
  any account, not the one it was first used on.
- Facts that vary from user to user come from the user's project at run time. The skill tells the agent where to find
  them, such as the project's `AGENTS.md`, a `README.md`, or a configuration file, and what to do when they are
  missing. Examples of such facts are the people involved, the number of units, the heating type, the property
  manager, or the paths of a project.
- A rule learned in one project is stated in general terms, as a mechanism that applies to the next case. The
  `writing-for-agents` skill describes how (section Pruning, "lesson").

## Keep recipes short

- A recipe in a skill's `.just` file only calls a script. Logic longer than a few lines lives in a script in the
  skill's `scripts/` folder, a shell script (`.sh`) for shell code, so it can be read, run, and checked on its own.
- The `.just` file stays where projects import it from, so moving logic into a script does not change their
  `import` line.

## Keep personal and project information out

- A skill, its scripts, and its examples contain no personal or project information. That covers names of people and
  companies, addresses, property, unit, customer, and account numbers, IBANs, amounts, dates, and file or folder names
  taken from a real project.
- Examples use invented values that look realistic, such as "Musterstraße 1", "Einheit 3", or "DE00 0000 0000 0000
  0000 00".
- Before a commit, every added or changed line is checked for such information. A finding is rewritten in general
  terms or replaced by an invented value.
