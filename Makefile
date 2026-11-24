.PHONY: install lint format format-check typecheck test coverage verify docs-metrics licenses build build-check \
        scan scan-dist acceptance acceptance-wheel acceptance-dist demo site publish-testpypi publish-pypi clean check-uv

UV := uv
PY_VERSION ?= 3.12

check-uv:
	@command -v $(UV) >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }

install: check-uv
	$(UV) sync --extra dev --python $(PY_VERSION)

# ── Quality ────────────────────────────────────────────────────────────────
lint:
	$(UV) run ruff check src tests

format:
	$(UV) run ruff format src tests

format-check:
	$(UV) run ruff format --check src tests

typecheck:
	$(UV) run mypy

test:
	$(UV) run pytest

coverage:
	$(UV) run pytest --cov=src/guage_kit --cov-report=term --cov-report=xml --cov-fail-under=85

docs-metrics:
	$(UV) run python scripts/gen_metric_docs.py

# Every runtime dependency (and the optional extras) must be permissively licensed.
licenses:
	$(UV) run --with packaging python scripts/check_licenses.py

verify: lint format-check typecheck test licenses
	$(UV) run python scripts/gen_metric_docs.py --check

# ── Build and scan ─────────────────────────────────────────────────────────
build: check-uv
	rm -rf dist
	find src -name __pycache__ -type d -prune -exec rm -rf {} +
	$(UV) build

build-check: build
	$(UV) run --with twine twine check dist/*

# Scan the built wheel and sdist the way package firewalls do (secrets, vulnerable dependencies, malicious-code
# heuristics, inventory) with free tools: gitleaks, pip-audit, GuardDog, Bandit. Report in scan-report/.
scan: build scan-dist

scan-dist:
	$(UV) run --no-project python scripts/scan_dist.py --dist dist --out scan-report $(SCAN_ARGS)

# ── Acceptance (capability scenarios + release gate) ───────────────────────
ACCEPTANCE_VENV := .acceptance-venv
ACCEPTANCE_EXTRAS ?=
ACCEPTANCE_ARGS ?=
ACCEPTANCE_PINS ?=

acceptance:
	$(UV) run --frozen pytest acceptance -n auto -p no:cacheprovider $(ACCEPTANCE_ARGS)

acceptance-wheel: build
	$(MAKE) acceptance-dist

# Against an already-built dist/*.whl (CI tests the exact artifact it publishes).
acceptance-dist:
	rm -rf $(ACCEPTANCE_VENV)
	$(UV) venv -q --python $(PY_VERSION) $(ACCEPTANCE_VENV)
	$(UV) pip install -q --python $(ACCEPTANCE_VENV)/bin/python "$$(ls -t dist/*.whl | head -1)$(if $(ACCEPTANCE_EXTRAS),[$(ACCEPTANCE_EXTRAS)])" \
	  pytest pytest-bdd pytest-xdist pyyaml $(ACCEPTANCE_PINS)
	ACCEPTANCE_BIN_DIR=$(CURDIR)/$(ACCEPTANCE_VENV)/bin $(ACCEPTANCE_VENV)/bin/python -m pytest acceptance \
	  -n auto -p no:cacheprovider $(ACCEPTANCE_ARGS)

# ── Demo and website ───────────────────────────────────────────────────────
demo:
	$(UV) run guage demo -o guage-demo

site:
	$(UV) run guage demo -o website/public/demo --profile private
	cd website && npm ci && npm run build

# ── Publish (tokens come from .env: UV_PUBLISH_TOKEN, UV_PUBLISH_TOKEN_TESTPYPI) ──
publish-testpypi: build
	@set -a; [ -f .env ] && . ./.env; set +a; \
	  $(UV) publish --publish-url https://test.pypi.org/legacy/ --token "$$UV_PUBLISH_TOKEN_TESTPYPI"

publish-pypi: build
	@set -a; [ -f .env ] && . ./.env; set +a; \
	  $(UV) publish --token "$$UV_PUBLISH_TOKEN"

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml scan-report $(ACCEPTANCE_VENV) guage-demo
