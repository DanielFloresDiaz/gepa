---
name: release
description: >-
  Prepare GEPA releases from develop-to-main branch deltas or release context.
  Inspects git history, writes versioned changelogs, bumps pyproject.toml,
  updates README, and runs CI-equivalent validation (pre-commit, build,
  typecheck, test) on the release branch — all must pass before finishing.
  Use when cutting a GEPA release, bumping versions, generating changelog or
  release notes, or asking what is unreleased between develop and main.
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

Validation checks the **branch being released** (typically `develop`), not only the release-artifact files you edited. A release is **not complete** until every check below passes. Do not defer failures as “pre-existing”, “unrelated to the changelog”, or “already on the branch” — fix them before finishing.

These mirror `.github/workflows/testing.yaml` (`lint`, `typecheck`, `test`). Respect an explicit user request to skip tests; otherwise run all of them.

From the `gepa/` directory, in order:

```bash
make pre-commit   # lint job: hooks + format + ruff (same as CI pre-commit)
uv build          # lint job: package must build
make typecheck
make test
```

**Rules:**

1. **All commands must exit 0** before you report the release as done.
2. If any command fails, fix the underlying code or config, then re-run the **full** sequence until green. Follow `.cursor/skills/python-refactoring/SKILL.md` while fixing Python/type issues and `.cursor/skills/python-testing/SKILL.md` after code fixes.
3. Do not skip `make typecheck` or `make test` just because your edits were changelog, README, or version bumps — CI still runs them on push.
4. Do not finish with a deliverable that lists failed validation; either fix failures or stop and report what is blocking release.
5. If pre-commit’s format hook reformats files, stage those changes and run the full sequence again.

Only note skipped checks when the user explicitly asked to skip them.

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
- Validation results — **all checks passed**, or which check is still failing and what you fixed (only omit checks if the user explicitly requested skipping them)

Do not commit unless the user asks.
