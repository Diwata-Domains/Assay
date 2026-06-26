## [0.3.3] — 2026-06-26

### Bug Fixes
- robust GitHub Action install (current Playwright, isolated dir, pinned floor)
- install Assay from local checkout (published version lacks --no-docker)
- use current Playwright (1.44.0 stale for Ubuntu 24.04 libasound2t64)
- install Playwright in isolated tempdir (monorepo workspace:* breaks npm)
- use python -m pip + fuller assay.toml in visual-regression capture
- add skipLibCheck so vitest .d.ts types don't break apex/conclave build

### Chores
- set version to 0.3.2 (match published; merge mis-resolved to 0.3.1)
- re-enable visual-regression PR verify + pin assay-kit==0.3.2 (now installable)
- onboard Scry as its own workspace + create Phase 1 backlog packets; upgrade tooling
- keep visual-regression dispatch-only (blocked: assay-kit warden dep not on PyPI)
- pin assay-kit==0.3.1 (bare install backtracks to a flagless older build)
- use published assay-kit + restore PR-verify trigger (0.3.1 has --no-docker)
- make visual-regression dispatch-only until Assay runs in CI (non-breaking)
- add committed-baseline visual regression (apex/conclave/sovereign)

### Tests
- add visual-regression baselines for apex/conclave/sovereign
- scaffold Vitest + Testing Library for apex, conclave, sovereign

### Documentation
- backlog — Scry->Grain task-packet loop spec (ready to import into Grain)

### Features
- canary health-check (mirror) + LinkedIn profile health default
- wire grain-assay frontend gate + reusable Assay verify workflow
- health/run-log (drift detection) + LinkedIn selectors/login-wall/pipeline
- interactive user-triggered session-capture tool
- private LinkedIn AuthenticatedFetcher adapter (Layer 3 moat)

## [0.3.2] — 2026-06-25

### Chores
- relock for assay vendored-warden dep change (warden out, starlette in)
- sync visual-regression (dispatch-only, warden blocker noted) to main

### Bug Fixes
- vendor warden to make assay-kit pip-installable

## [0.3.1] — 2026-06-25

### Chores
- sync visual-regression workflow (dispatch-only) to main
- add visual-regression workflow to main (enables manual capture + PR verify)

## [0.3.0] — 2026-06-25

### Documentation
- scaffold telemetry-layer planning workspace
- reconcile drifted planning docs to one truth (Phase 28)

### Features
- add cross-document doc-drift checks to docs audit

# Changelog

All notable changes to assay-kit are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.2.0] — 2026-06-11

### Added
- **`assay init`** — interactive first-run setup wizard; prompts for project name, output directory, port, admin email, and password; writes `assay.toml` and prints the corresponding `.env` block; `--force` flag to overwrite an existing config
- **`AssaySDK.fromEnv()`** — static factory that reads `VITE_ASSAY_API_KEY` / `ASSAY_API_KEY` and `VITE_ASSAY_ENDPOINT` / `ASSAY_ENDPOINT` from environment; works in both Vite/React (import.meta.env) and Node/server contexts
- **`useAssayCapture()` React hook** (`assay-sdk/react`) — wraps `sdk.capture()` with `capturing`, `lastResult`, and `error` state; accepts an optional pre-constructed `sdk` instance or falls back to `AssaySDK.fromEnv()`; exported from `@diwata/assay-sdk/react` subpath
- **`assay key create` improvements** — after creating a key, the CLI now prints a ready-to-run curl test command and an SDK usage snippet so the key can be verified and wired in immediately
- **Framework setup guides** — `docs/setup-vite-react.md` and `docs/setup-nextjs.md` covering env var naming, SDK construction, and hook usage for each framework
- **`/health` endpoint** — lightweight health probe for gateway/compose healthchecks

### Changed
- `assay-sdk` package now exports a `./react` subpath (`dist/esm/react.js` / `dist/cjs/react.js`) alongside the default export; `peerDependencies` adds optional `react >=18`

### Notes
- `Development Status :: 3 - Alpha` retained
- The `useAssayCapture` hook requires React 18+; the core SDK has no React dependency

---

## [0.1.0] — 2026-04-01

Initial public release.

### Included
- `assay serve` — run the Assay HTTP server with SQLite or Postgres backend
- `assay admin set-password` — set or reset the admin password from the CLI
- `assay key create / list / revoke` — API key management for project integrations
- `POST /ingest` — capture endpoint accepting `X-Assay-Key` authenticated payloads
- `AssaySDK({ apiKey, endpoint })` — TypeScript SDK with `sdk.capture()` method
- JWT-based admin authentication
- `assay.toml` project configuration format
