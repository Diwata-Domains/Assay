PYTHON := .venv/bin/python
PYTEST  := .venv/bin/pytest
RUFF    := .venv/bin/ruff
MYPY    := .venv/bin/mypy

.PHONY: test lint typecheck

test:
	$(PYTEST) tests/
	cd sdk && npm test

lint:
	$(RUFF) check src/ tests/
	$(RUFF) format --check src/ tests/
	cd sdk && npx tsc --noEmit 2>/dev/null || true

typecheck:
	$(MYPY) src/assay/
	cd sdk && npx tsc --noEmit
