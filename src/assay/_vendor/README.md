# Vendored dependencies

## `warden`

`warden` is Diwata's shared auth library (JWT issuance/verification + a Starlette
session-cookie middleware). It lives in this repo at `packages/warden/` but is
**not published to PyPI**, so depending on it directly made the published
`assay-kit` wheel uninstallable.

To keep `assay-kit` self-contained and cleanly `pip install`-able, the warden
modules are vendored here verbatim. Internal `from warden.X import ...` statements
were rewritten to relative imports (`from .X import ...`); third-party imports
(`jwt`, `starlette`) are unchanged. The only runtime dependencies are the public
`PyJWT` and `starlette` packages, both declared in `products/assay/pyproject.toml`.

Assay imports it as `from assay._vendor.warden import ...`.

**Re-sync when warden changes:** copy the modules from `packages/warden/warden/`
(`__init__.py`, `config.py`, `exceptions.py`, `middleware.py`, `session.py`,
`tokens.py`, `py.typed`) and re-apply the absolute→relative import rewrite.
