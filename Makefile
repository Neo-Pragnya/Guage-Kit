.PHONY: format lint type test docs build release

format:
	uv run ruff fix . || true
	uv run black .
	uv run isort .

lint:
	uv run ruff check .
	uv run black --check .
	uv run isort --check-only .

type:
	uv run mypy src

test:
	uv run pytest -q --cov=guage_kit --cov-report=term-missing

docs:
	uv run sphinx-build -b html docs docs/_build/html -W

build:
	uv run python -m build

release: build
	uv run twine upload dist/*