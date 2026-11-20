---
name: development
description: >-
  How to develop GEPA (the DanielFloresDiaz fork used by brawler) and validate
  every change: package layout, setup with uv, code style (double quotes, no
  relative imports), static checks (make pre-commit, make typecheck), pytest with
  the 70% coverage gate, the mkdocs site and generated API docs, and the user's
  project rules. Use when implementing, refactoring, testing, or fixing anything
  in src/gepa/, tests/, or docs/.
license: MIT
---

# GEPA development guide

`AGENTS.md` (loaded through `CLAUDE.md`) gives the project overview. This skill adds the validation loop and the fork-specific notes.

## Layout

| Path | Role |
|---|---|
| `src/gepa/core/` | Optimization loop, state, evaluation |
| `src/gepa/proposer/` | Candidate proposal and mutation |
| `src/gepa/adapters/` | Integration adapters (DSPy, RAG, MCP, …) |
| `src/gepa/strategies/` | Batch sampling and candidate selection |
| `src/gepa/logging/` | Experiment tracking |
| `tests/` | pytest suite |
| `docs/` | mkdocs site (`docs/docs/`, `mkdocs.yml`, `scripts/generate_api_docs.py`) |
| `examples/` | Usage examples |

This repo is a fork that brawler consumes through a git tag pin (`gepa = { git = "…/gepa.git", tag = "vX.Y.Z" }`). Public API changes reach brawler only after a release and a pin bump there, so keep `optimize` / `optimize_anything` and the callbacks backward compatible unless the release is marked breaking.

## Setup and style

```bash
make install    # uv sync + pre-commit hooks
```

Use uv for every Python execution. Ruff runs with line length 120, **double quotes** (unlike the Solomon repos), and no relative imports. Pyright checks types. Target Python is 3.13+.

## Static checks

After modifying `src/gepa/**/*.py`, `tests/**/*.py`, `pyproject.toml`, or `uv.lock`, from `gepa/`:

```bash
make pre-commit   # hooks + ruff format + ruff check
make typecheck    # pyright
uv build          # CI's lint job also builds the package
```

Fix every error and re-run if hooks rewrote files. Stale `exclude-newer` metadata in `uv.lock` can cause lockfile churn that only shows up in CI. Keep the hook's changes and re-run.

## Tests

```bash
make test                          # pytest with coverage (CI requires ≥ 70% total)
uv run pytest tests/<path> -vv     # one area while iterating
make testcov                       # + coverage report
```

Give every test a docstring (one sentence for simple tests; scenario, setup, and protected behavior for complex ones).

## Docs

When public symbols, adapters, or guides change, update the mkdocs pages in `docs/docs/` and validate the generated API docs the same way `docs.yml` does:

```bash
cd docs && uv pip install -r requirements.txt && uv run python scripts/generate_api_docs.py --validate --skip-adapters
uv run mkdocs build    # when navigation or pages changed
```

## What to run after a change

| Change | Run |
|---|---|
| Python | Static checks, then the tests for the touched area |
| Public API, adapters, callbacks | The above + `README.md` (Quick Start, `optimize_anything`, Adapters, Integrations) + docs validation |
| Layout or commands | `AGENTS.md`, `CONTRIBUTING.md`, and this skill |

Use the `release` skill to cut a version.

## Related skills

- `release`

## Project rules

Rules the user has set for this repository. They override the defaults above. Add an entry whenever the user states one (see "Keeping this skill current"), using the format `- YYYY-MM-DD: <rule>. <reason, if given>`.

_None recorded yet._

## Keeping this skill current

This skill is versioned with the repository, so it must evolve with it. Update it **in the same change**, not as a follow-up, whenever:

- **Something changes:** layout, commands or Make targets, env vars, ports, generated artifacts, CI workflows, cross-repo contracts, or dependency pins. Also when you find a statement here that is wrong or stale.
- **The user sets a rule:** a preference, convention, or prohibition ("never use X", "always do Y", "don't touch Z", a frontend pattern to avoid). Record it under **Project rules** (in this file), with the date (YYYY-MM-DD) and the reason if given. Rules about how code is written go in the `development` skill. Rules about how versions ship go in the `release` skill.
- **You learn something reusable:** a pitfall you hit, a mistake a line here would have prevented, or a non-obvious procedure you worked out. Add it to the section it belongs to.
- **A task repeats:** if it is not covered by `development` or `release`, create a new skill at `.claude/skills/<kebab-name>/SKILL.md` (frontmatter `name` = the folder name, plus a `description` that says what it does and when to use it), and list it under "Related skills" in the `development` skill.

How to edit:

- Check every path, command, and target against the repo before writing it down.
- Keep it short. Edit the existing section instead of appending duplicates, and delete what is no longer true.
- Never record secrets, tokens, personal data, or one-off details of a single task.
- An explicit instruction from the user in the current conversation wins over a recorded rule. If they change a rule, update the entry.
- Tell the user in your final message which skill you changed and why. The skill file is part of this repository (often a git submodule), so include it when they ask you to commit.
