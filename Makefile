.PHONY: install test lint format check clean

install:
	python -m pip install -e ".[dev,browsers]"

test:
	pytest

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

check: lint test

clean:
	rm -rf build dist .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
