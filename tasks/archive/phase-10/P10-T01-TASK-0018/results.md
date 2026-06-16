# Results: P10-T01-TASK-0018

## Packet State
- **Current Task Status:** done
- **Review Readiness:** approved
- **Recommended Next Status:** done

## Summary

Created `.github/workflows/release.yml` triggered on `v*.*.*` tags. Builds sdist + wheel via `python -m build`, publishes via `pypa/gh-action-pypi-publish` with OIDC trusted publisher (no stored token). Updated `src/assay/__init__.py` to source `__version__` from `importlib.metadata` with `PackageNotFoundError` fallback to `0.0.0+dev`.

## User Review
- **State:** approved
- **Summary:** Implemented as specified.
- **Resolution Mode:** close_task

### Required Fixes
- None

### Residual Risks
- PyPI trusted publisher environment must be configured before first tagged release

## Closure Decision
- **Decision:** closed
- **Reason:** Deliverable complete and verified.
