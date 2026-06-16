# Task: PyPI publish workflow (GitHub Actions release job)

## Metadata
- **ID:** TASK-0018
- **Status:** done
- **Phase:** Phase 10 — Distribution + CI
- **Backlog:** P10-T01
- **Packet Path:** tasks/P10-T01-TASK-0018/
- **Dependencies:** Phase 9 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Create `.github/workflows/release.yml` to publish Assay to PyPI automatically when a version tag is pushed. Use `python -m build` to build sdist + wheel and `pypa/gh-action-pypi-publish` with trusted publisher (OIDC, no token needed).

## Why This Task Exists
Phase 10 goal: make Assay installable anywhere via `pip install assay` without cloning the repo.

## Scope
- `.github/workflows/release.yml` triggered on `v*.*.*` tags
- `python -m build` + PyPI publish via trusted publisher
- `__version__` sourced from `importlib.metadata` so it reflects the installed tag

## Constraints
- Must not hardcode PyPI tokens — use OIDC trusted publisher
- Version in `__init__.py` must read from `importlib.metadata`, not a hardcoded string

## Escalation Conditions
- PyPI trusted publisher environment must be configured by the operator before the first release
