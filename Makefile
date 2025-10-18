.PHONY: install check test clean

install: ## Install dependencies
	uv sync

check: ## Format, lint, and type-check code
	@echo "Formatting code with ruff..."
	@uv run ruff format .
	@echo "Linting code with ruff..."
	@uv run ruff check . --fix
	@echo "Type-checking code with pyright..."
	@uv run pyright
	@echo "All checks passed!"

test: ## Run tests
	@echo "Running tests..."
	@uv run pytest

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
