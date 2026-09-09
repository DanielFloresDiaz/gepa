---
name: python-refactoring
description: >-
  Validation after editing Python code in GEPA (src/gepa/, tests/, Python config).
  Runs make pre-commit and make typecheck. Not for documentation, changelogs,
  or non-Python files. Use when refactoring or modifying Python source, tests,
  or configuration in the GEPA package.
license: MIT
---

# Python refactoring validation

This skill applies **only** to Python work in the GEPA package. It is **not** a general file-editing policy.

## When to use

Use after modifying Python code or Python configuration, for example:

- `src/gepa/**/*.py`
- `tests/**/*.py`
- `pyproject.toml`, `uv.lock` when Python dependencies or tooling changed

## When not to use

**Do not** run these commands for:

- Documentation (`README.md`, `docs/`, `changelogs/`)
- CI YAML, locale files, or other non-Python artifacts
- Markdown-only or config-only edits outside Python tooling

For releases, use `.cursor/skills/release/SKILL.md`.

## Required commands

After Python edits, from the `gepa/` directory:

```bash
make pre-commit
make typecheck
```

Fix formatting, hook, and type errors before considering the refactor complete.

## Companion skill

When Python **tests** also need to run (not just static checks), see `.cursor/skills/python-testing/SKILL.md`.
