---
name: python-testing
description: >-
  Run pytest for GEPA after code or test changes. Not for documentation or
  general testing. Use when validating Python behavior, fixing failing tests,
  or confirming pytest coverage for src/gepa/ and tests/ changes.
license: MIT
---

# Python testing

This skill covers **pytest for GEPA only**. It is **not** a general testing guide.

## When to use

Run tests after modifying:

- `src/gepa/**/*.py`
- `tests/**/*.py`
- Python fixtures or conftest that affect package behavior

## When not to use

**Do not** run tests for:

- Documentation, changelogs, or README edits
- Release metadata or CI YAML-only changes
- Tasks where the user explicitly asked to skip tests

## Required command

From the `gepa/` directory:

```bash
make test
```

Or directly:

```bash
uv run pytest tests/
```

## With static checks

When you also changed Python source (not test-only tweaks), run refactoring validation first:

1. `make pre-commit` and `make typecheck` — see `.cursor/skills/python-refactoring/SKILL.md`
2. `make test`

## Quality expectations

- Tests should pass before Python changes are considered stable.
- Every test should include a short summary docstring.
- Simple tests: one sentence. Complex tests: explain scenario, setup, and protected behavior.
