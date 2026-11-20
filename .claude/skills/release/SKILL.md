---
name: release
description: >-
  Prepare a GEPA release from the develop-to-main delta. Inspects git history,
  writes the versioned changelog, bumps pyproject.toml, reconciles README, the
  mkdocs site and generated API docs, and runs the CI-equivalent gate
  (pre-commit, build, typecheck, tests with coverage, docs validation) on the
  release branch; every check must pass before finishing. Use when cutting a
  GEPA release, bumping the version, writing release notes, checking release
  readiness, or asking what is unreleased between develop and main.
license: MIT
---

# GEPA release workflow

GEPA (Genetic-Pareto) is the prompt and text optimization framework. This repo is the DanielFloresDiaz fork, used by **brawler** through a git tag pin (`gepa = { git = "ssh://git@github.com/DanielFloresDiaz/gepa.git", tag = "vX.Y.Z" }`). A `v<version>` tag runs `release.yaml`: tests, then a wheel build, then a GitHub release with the changelog body. `docs.yml` builds and deploys the mkdocs site.

Run all commands from the `gepa/` directory.

## 1. Branch analysis

Default range: `main..develop`. If the user says to **omit uncommitted changes**, use only committed history.

1. `git fetch origin`, then `git log main..develop --format='%h %s' --reverse`, and read the commit bodies.
2. `git diff main..develop --stat`, then open: `src/gepa/core/`, `proposer/`, `adapters/`, `strategies/`, `logging/`, the public `optimize` / `optimize_anything` API and callbacks, `pyproject.toml` extras.
3. Group the findings into user-facing areas.

**Changelog scope:** include the public API, optimization behavior, adapters and integrations, logging and tracking, extras and packaging, and documented config. Leave out tooling, `.claude/` config, CI, and refactors or tests with no visible effect. If the delta is all internal, do not release unless asked. A summary-only request gets the range, the commit count, and the grouped summary, with no edits.

## 2. Version and changelog

- Use three-segment semver. The current version is the highest `changelogs/v*.md`, compared numerically, and it must equal `pyproject.toml` `version`. Use PATCH for fixes and MINOR for features, or for breaking changes on `0.x`. Use MAJOR only on request.
- Mirror the latest `changelogs/v*.md` (`# Changelog`, `## [<version>] - YYYY-MM-DD`, a summary paragraph, `**Section:**` headings with `*` bullets). Write `changelogs/v<version>.md` and an exact copy at `latest.md`. The heading has no `v`, and the tag `v<version>` matches the filename. Use today's date and end each file with one trailing newline.

### Semantic versioning rules

These rules apply to every version this skill produces. The repo-specific bump guidance above decides which segment moves.

- **Format:** `MAJOR.MINOR.PATCH`, exactly three non-negative integers with no leading zeros (`0.13.0`, never `0.13`, `v0.13`, or `0.013.0`). Add a pre-release only when the user asks: `-rc.1` in npm and Cargo versions, the PEP 440 form (`0.2.0rc1`, `0.0.1b0`) in Python packages.
- **Ordering:** compare segment by segment as integers, never as strings (`0.10.0` > `0.9.0`, `0.2.10` > `0.2.9`). The current version is the highest released one, and the new one must be strictly greater.
- **Bumps:** MAJOR for incompatible changes to the public surface (API, wire or gRPC contract, CLI flags, env vars, config, schema, exported symbols). MINOR for backward-compatible features. PATCH for backward-compatible fixes. Increment exactly one segment and reset the lower ones to `0`.
- **`0.y.z`:** the public surface is not yet stable. Breaking changes bump MINOR. Never move to `1.0.0` or any new MAJOR without an explicit user request.
- **Immutability:** never reuse, decrease, or retag a published version. If a pushed tag is wrong, fix forward with a new PATCH.
- **No-op deltas:** if nothing consumer-visible changed, do not bump. Report that instead.
- **One version everywhere:** the manifest, the lockfile entry, the changelog filename and heading, README badges and mentions, any generated spec (`info.version`), and the git tag (with the `v` prefix where the workflow expects it) carry the same number.

## 3. Release readiness

Validation checks the **branch being released** (usually `develop`), not just the files you edited. Do not defer failures as "pre-existing" or "unrelated", because CI runs these on push. Respect an explicit request to skip tests, and otherwise run everything.

### 3.1 Versions agree

- [ ] `pyproject.toml` `version` = `<version>`, and the `gepa` entry in `uv.lock` matches (`uv lock`)
- [ ] `README.md` badges and inline versions
- [ ] `changelogs/v<version>.md` = `latest.md`

### 3.2 Docs match the release

- [ ] `README.md`: Installation (extras), Quick Start, `optimize_anything`, How It Works, Adapters, Integrations.
- [ ] mkdocs site (`docs/docs/`): guides, tutorials, and the API pages for changed symbols. Then validate the generated API docs as `docs.yml` does:

  ```bash
  cd docs && uv pip install -r requirements.txt && uv run python scripts/generate_api_docs.py --validate --skip-adapters
  ```

  Run a full `uv run mkdocs build` from `docs/` when navigation or pages changed.
- [ ] `AGENTS.md` (project structure, commands) and `CONTRIBUTING.md` when layout or workflow changed.

### 3.3 Gate (mirrors `testing.yaml`)

```bash
make pre-commit   # hooks + ruff format + ruff check
uv build          # the package must build
make typecheck    # pyright
make test         # pytest with coverage (CI threshold: 70%)
```

1. Every command must exit 0.
2. If any fails, fix the code or config and re-run the **full** sequence. Follow the `development` skill (static checks and tests) while fixing.
3. Don't skip typecheck or tests because the edits were "only" changelog or version changes.
4. If pre-commit reformats files or touches `uv.lock`, keep those changes and re-run. Stale `exclude-newer` metadata in `uv.lock` can cause lock churn that only shows up in CI.

## 4. Tagging and follow-ups

After `develop` is merged into `main`, and only when the user asks: `git tag v<version> && git push origin v<version>`. Then report the follow-up: brawler bumps `gepa = { …, tag = "v<version>" }` in its `pyproject.toml`, re-locks, and records the new submodule SHA.

## 5. Deliverable

Report the range and commit count, the grouped summary, the version and date, the files changed, the README and docs updates, and the validation results: **all passed**, or exactly what still fails and what you fixed. Do not commit unless asked.

### Pull request title and summary

Always finish the deliverable with a ready-to-paste text for the release pull request (the source branch of the range from section 1 into its target). The user copies it into GitHub, so do not open the PR yourself. Give it as two separate fenced `markdown` blocks, one labelled **PR title** and one labelled **PR summary**, so each copies in one click.

- **PR title:** one line, 70 characters or fewer, in the form `Release v<version>: <the one or two headline changes>`. No trailing period.
- **PR summary:** written for reviewers, from the changelog and the actual diff, not from memory:
  - `## Summary`: two or three sentences on what ships and why it matters.
  - `## Changes`: the changelog bullets, grouped by area, consumer-facing items only.
  - `## Breaking changes / migration`: what downstream repos or operators must do. Omit the section when there is nothing.
  - `## Release checklist`: the version, the files that carry it, and each readiness check marked pass, fixed, or skipped (with the reason). Never mark a check as passed that was not run.
  - `## Follow-ups`: the steps that happen after the merge (tag, downstream pin bumps, submodule SHAs).
- Keep the title and summary consistent with `changelogs/v<version>.md`: same version, same facts. If there is no release (a no-op delta), say so instead and give no PR text.

## Release rules

Release-specific rules the user has set for this repository. They override the steps above. Use the format `- YYYY-MM-DD: <rule>. <reason, if given>`.

_None recorded yet._

## Keeping this skill current

This skill is versioned with the repository, so it must evolve with it. Update it **in the same change**, not as a follow-up, whenever:

- **Something changes:** layout, commands or Make targets, env vars, ports, generated artifacts, CI workflows, cross-repo contracts, or dependency pins. Also when you find a statement here that is wrong or stale.
- **The user sets a rule:** a preference, convention, or prohibition ("never use X", "always do Y", "don't touch Z", a frontend pattern to avoid). Record it under **Release rules** (in this file), with the date (YYYY-MM-DD) and the reason if given. Rules about how code is written go in the `development` skill. Rules about how versions ship go in the `release` skill.
- **You learn something reusable:** a pitfall you hit, a mistake a line here would have prevented, or a non-obvious procedure you worked out. Add it to the section it belongs to.
- **A task repeats:** if it is not covered by `development` or `release`, create a new skill at `.claude/skills/<kebab-name>/SKILL.md` (frontmatter `name` = the folder name, plus a `description` that says what it does and when to use it), and list it under "Related skills" in the `development` skill.

How to edit:

- Check every path, command, and target against the repo before writing it down.
- Keep it short. Edit the existing section instead of appending duplicates, and delete what is no longer true.
- Never record secrets, tokens, personal data, or one-off details of a single task.
- An explicit instruction from the user in the current conversation wins over a recorded rule. If they change a rule, update the entry.
- Tell the user in your final message which skill you changed and why. The skill file is part of this repository (often a git submodule), so include it when they ask you to commit.
