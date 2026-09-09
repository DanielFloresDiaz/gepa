.DEFAULT_GOAL := all

.PHONY: clean
clean: ## Remove all build artifacts
	rm -rf .coverage* *coverage* .mypy_cache .pytest_cache .ruff .ruff.lock .ruff_cache htmlcov *.log dist
	find . -name "__pycache__" -type d -exec rm -rf {} +

.PHONY: .uv
.uv: ## Check that uv is installed
	@uv --version || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: .pre-commit
.pre-commit: ## Check that pre-commit is installed
	@pre-commit -V || echo 'Please install pre-commit: https://pre-commit.com/'

.PHONY: pre-commit
pre-commit: .uv .pre-commit ## Run pre-commit hooks
	uv sync --extra dev --group lint --quiet > /dev/null 2>&1
	pre-commit run --all-files
	uv sync --extra dev --quiet > /dev/null 2>&1

.PHONY: install
install: .uv .pre-commit ## Install the package, dependencies, and pre-commit for local development
	uv sync --frozen --extra dev --group lint
	pre-commit install --install-hooks

.PHONY: sync
sync: .uv ## Update local packages and uv.lock
	uv sync --extra dev --group lint

.PHONY: format
format: ## Format the code
	uv run ruff format
	uv run ruff check --fix --fix-only

.PHONY: lint
lint: ## Lint the code
	uv run ruff format --check
	uv run ruff check

.PHONY: typecheck
typecheck: ## Run static type checking
	@# PYRIGHT_PYTHON_IGNORE_WARNINGS avoids the overhead of making a request to github on every invocation
	uv sync --extra dev --group lint --quiet > /dev/null 2>&1
	PYRIGHT_PYTHON_IGNORE_WARNINGS=1 uv run pyright
	uv sync --extra dev --quiet > /dev/null 2>&1

.PHONY: test
test: ## Run tests and collect coverage data
	uv run coverage run -m pytest -vv tests/

.PHONY: testcov
testcov: test ## Run tests and generate a coverage report
	@echo "building coverage html"
	@uv run coverage report
	@uv run coverage html --show-contexts --title "Coverage Report"
	@uv run coverage xml

.PHONY: all
all: format lint typecheck testcov ## Run code formatting, linting, static type checks, and tests with coverage report generation

.PHONY: help
help: ## Show this help (usage: make help)
	@echo "Usage: make [recipe]"
	@echo "Recipes:"
	@awk '/^[a-zA-Z0-9_-]+:.*?##/ { \
		helpMessage = match($$0, /## (.*)/); \
		if (helpMessage) { \
			recipe = $$1; \
			sub(/:/, "", recipe); \
			printf "  \033[36m%-20s\033[0m %s\n", recipe, substr($$0, RSTART + 3, RLENGTH); \
		} \
	}' $(MAKEFILE_LIST)
