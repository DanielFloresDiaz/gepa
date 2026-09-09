---
name: release
description: >-
  Prepare GEPA releases from develop-to-main branch deltas or release context.
  Inspects git history, writes versioned changelogs, bumps pyproject.toml,
  updates README, and runs release validation. Use when cutting a GEPA release,
  bumping versions, generating changelog or release notes, or asking what is
  unreleased between develop and main.
license: MIT
---

# GEPA release workflow

Prepare releases for the **GEPA** package (`gepa/`). All commands run from the `gepa/` directory unless noted.

## Branch analysis

Default compare range: `main..develop` (`target..source`).

If the user says to **omit uncommitted changes**, base analysis only on the committed branch range (`git log target..source`, `git diff target..source`).

Do not stop at `git log --oneline`.

1. List commits chronologically: `git log target..source --format='%h %s' --reverse`.
2. Read commit bodies when present.
3. Review stats: `git diff target..source --stat`.
4. Open behavior-heavy diffs for API, optimization engine, adapters, and config changes.
5. Group related commits into user-facing areas.

**Exclude from the changelog** anything that does not affect consumers of the package — runtime behavior, public API, published package surface, or operator-facing configuration. Do not mention:

- Removal or addition of internal dev tooling, editor config, or CI-only changes with no user impact
- Refactors, tests, or docs that only support development workflow unless they change documented public behavior

If a commit mixes product and non-product changes, include only the product-facing parts. When the branch delta is entirely non-product work, do not cut a release unless the user explicitly asks.

For summary-only requests, report the branch range, commit count, grouped summary, and optional commit-by-commit rundown. Skip release file edits.

## Changelog format

Mirror recent files such as `changelogs/v0.1.1.md`.

```markdown
# Changelog

## [<version>] - YYYY-MM-DD

<One short active-voice summary paragraph.>

**Section title:**

* Bullet describing what changed and why it matters.
```

Rules:

- Create `changelogs/v<version>.md` and update `changelogs/latest.md` to match **exactly**.
- Document **product changes only** — see branch analysis exclusions above.
- User-facing, active voice; no code snippets unless essential.
- End every edited file with exactly one trailing newline.

Typical section themes: optimization engine and strategies, adapters and integrations, API surface (`optimize`, callbacks), configuration and docs, minor fixes and type improvements.

## Version selection

Use [semver](https://semver.org/). The new version must exceed the highest `changelogs/v*.md` (ignore `latest.md`). Use today's date in `## [<version>] - YYYY-MM-DD`.

Infer bump from the unreleased delta unless the user gives an explicit version:

| Bump | When |
|---|---|
| **PATCH** | Bug fixes, docs, internal-only changes |
| **MINOR** | New features without breaking changes |
| **MAJOR** | Breaking changes or removals |

Prefer **MINOR** over **MAJOR** for `0.x` unless the user asks for a major bump.

## Release artifacts

- `changelogs/v<version>.md` and `changelogs/latest.md`
- `pyproject.toml` version (must match the Git tag, e.g. tag `v0.1.2` → version `0.1.2`)
- `uv.lock` if version bump requires it (via `uv lock`)
- `README.md` — version badge, recent releases, outdated API/behavior sections

### README consistency

1. Read the full `README.md`.
2. Reconcile with the changelog; extend existing sections, do not paste the changelog.
3. Update version badges and inline version references.
4. Document new APIs, breaking changes, or migration steps consumers need.

## Validation

Respect user instructions (e.g. skip tests). For Python changes in the release, follow `.cursor/skills/python-refactoring/SKILL.md` and `.cursor/skills/python-testing/SKILL.md`. Do not run those Python checks for documentation-only release edits.

From the `gepa/` directory:

```bash
make pre-commit
make typecheck
make test
```

Fix hook, formatting, or build failures before finishing.

## Tagging and publishing

After merging `develop` → `main`:

1. Tag from `main`: `git tag v<version>` (e.g. `v0.1.2`)
2. Push the tag: `git push origin v<version>`
3. The `release.yaml` workflow runs tests, builds wheels, and creates a GitHub release with the changelog body.

## Deliverable

Report briefly:

- Compared branch range and commit count
- Grouped summary of unreleased changes
- New version and date
- Files created or updated
- README changes (or version-only updates)
- Validation results (note skipped checks if applicable)

Do not commit unless the user asks.
