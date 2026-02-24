.PHONY: lint test format install all

install:
	pip install -e ".[dev]"

format:
	ruff format .

lint:
	mypy main.py --strict
	ruff check .
	ruff format --check .
	vulture . --min-confidence 80

test:
	pytest --cov=. --cov-fail-under=80

all: lint test
