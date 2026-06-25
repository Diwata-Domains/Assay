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
