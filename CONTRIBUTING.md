## Environment Setup

Python 3.10 or later is required.

Setting up your GEPA development environment requires you to fork the GEPA repository and clone it locally.
If you are not familiar with the GitHub fork process, please refer to [Fork a repository](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo). After creating the fork, clone
it to your local development device:

```shell
git clone https://github.com/DanielFloresDiaz/gepa
cd gepa
```

Next, set up a Python environment with the correct dependencies using [uv](https://github.com/astral-sh/uv):

```shell
make install
```

This installs all dependencies, the lint tooling group, and pre-commit hooks.

To verify that your environment is set up successfully, run the test suite:

```shell
make test
```

## Branch Strategy

GEPA uses a **develop → main** workflow:

- **`develop`** — integration branch; feature PRs target here
- **`main`** — release branch; merge `develop` into `main` when cutting a release
- Release tags (e.g. `v0.1.2`) are pushed from `main` and trigger the release workflow

## Development Commands

All commands run from the `gepa/` directory:

| Command | Description |
|---------|-------------|
| `make install` | Install dependencies and pre-commit hooks |
| `make sync` | Update packages from `uv.lock` |
| `make format` | Auto-format code with ruff |
| `make lint` | Check formatting and lint rules |
| `make typecheck` | Run pyright static type checking |
| `make test` | Run pytest with coverage collection |
| `make testcov` | Run tests and generate HTML/XML coverage reports |
| `make pre-commit` | Run all pre-commit hooks on all files |
| `make all` | Run format, lint, typecheck, and testcov |
| `make clean` | Remove build artifacts and caches |
| `make help` | Show all available targets |

## Code Linting with Ruff

We follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) and use `ruff` for both linting and formatting. Pre-commit hooks automatically run `make format` and `make lint` on commit.

```shell
make pre-commit
```

Or run hooks on staged files only:

```shell
pre-commit run
```

Please ensure all pre-commit checks pass before creating your pull request.

## Type Checking with Pyright

Run Pyright before opening a pull request to catch type regressions early:

```shell
make typecheck
```

You can target specific modules while iterating:

```shell
uv run pyright src/gepa/strategies/
```

## Releases

See `.cursor/skills/release/SKILL.md` for the full release workflow. In brief:

1. Merge `develop` → `main`
2. Bump `pyproject.toml` version and write `changelogs/v<version>.md`
3. Tag: `git tag v<version>` and `git push origin v<version>`
4. GitHub Actions builds wheels and publishes a GitHub release

## CI

- **`testing.yaml`** — lint, typecheck, test (Python 3.10–3.14), coverage (70% threshold)
- **`release.yaml`** — runs tests then publishes GitHub release with wheels on tag push
- **`docs.yml`** — MkDocs build and GitHub Pages deploy (unchanged)
