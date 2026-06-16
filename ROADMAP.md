# Roadmap

This document outlines the planned direction for Assay. It is intentionally high-level — no release dates, no feature promises. It reflects current intent and will change as the project evolves.

---

## Current — v0.2.0

The developer experience release. Assay gets easier to set up and wire into existing projects.

**Shipped in this release:**
- `assay init` — interactive first-run setup wizard; writes `assay.toml` and prints the `.env` block ready to paste
- `AssaySDK.fromEnv()` — static factory that reads env vars in both Vite/React and Node/server contexts
- `useAssayCapture()` React hook — `capturing`, `lastResult`, and `error` state; exported from `@diwata/assay-sdk/react`
- `assay key create` improvements — prints a ready-to-run curl test command and SDK snippet after key creation
- `/health` endpoint — lightweight probe for gateway and compose healthchecks
- Framework setup guides for Vite/React and Next.js

See [CHANGELOG.md](CHANGELOG.md) for the full list.

---

## Coming — v0.3.0

The visual verification release. Assay gains a full dashboard, pixel-level diff, and baseline management.

### Dashboard

A web UI served by `assay serve` at `/`. Browse every capture session, see pass/fail status at a glance, and drill into individual checks.

- Capture list with outcome, severity, screenshot thumbnail, and timestamp
- Packet detail view with full fields and inline screenshot
- Filter by project, date range, outcome, and severity

### Visual diff and baseline management

Pixel-level comparison of screenshots against approved baselines. Regressions are highlighted in red. Baselines are explicit — nothing changes silently.

- Before/after overlay slider in the dashboard
- Per-check approve or reject on baseline updates
- Diff stored as a separate artifact alongside the screenshot

### CI integration

- `assay run` exits non-zero on visual regression — safe to use as a blocking CI step
- Official GitHub Action (`uses: diwata-labs/assay-action@v1`) for zero-config CI wiring
- Status summary posted as a GitHub commit status or PR check

### Check library

Pre-built checks that run without a Playwright script:

- HTTP checks — status code, response time, redirect chain
- Header checks — `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`
- Auth checks — 401/403 on protected routes, session expiry behavior

### Script DSL

A JSON-based script format for defining capture sequences without writing Playwright directly. Covers navigation, form fill, click, wait, and capture steps.

---

## Later — v0.4.0

### Multi-viewport testing

Run the same test at multiple viewport widths in a single command. Diffs and baselines are tracked per viewport independently.

```bash
assay run --viewports mobile,tablet,desktop --target https://your-app.example.com
```

### Alerts and webhooks

- Webhook delivery on configurable events (`fail`, `regression`, `pass`)
- Pre-built Slack format with screenshot link
- SMTP email alerts on failure or regression

### Error and log visibility

Surfaces failures where they are useful rather than buried in SQLite.

- Dashboard error panel — filter by outcome, see error message and stack inline per packet
- `assay logs` CLI — tail the server and scheduler log files from the terminal
- `/errors` JSON endpoint — recent failures as structured JSON, consumable by CI and external tooling
- `/screenshots/{id}` serving endpoint — stable, shareable URLs for screenshots captured by the SDK

### Client access layer

Makes Assay usable as a verification backend for external clients without becoming a full multi-tenant platform.

- `POST /admin/keys` — programmatic key creation via the admin API, protected by the admin JWT; replaces the need to SSH in and run `assay key create` for each client
- Project-scoped keys — each API key is bound to a named project; ingest and reports are isolated per project
- Read-only viewer login — a client authenticates with their project key and sees only their project's dashboard; no access to other projects or admin functions

---

## Future — Assay Cloud

A hosted version of Assay for teams that do not want to run their own infrastructure.

The open-source CLI and SDK stay AGPL. The hosted platform is a separate commercial product — closed, paid, built on top of the same core. Key provisioning goes through an onboarding flow; clients get a login and project dashboard without any self-hosting required.

This is not on the short-term roadmap. The client access layer in v0.4.0 lays the foundation.

---

## Not on the Roadmap

These are explicit non-goals for the foreseeable future:

- Full multi-tenant SaaS with self-service account creation (Assay Cloud is operator-provisioned)
- Vendor lock-in to any specific CI provider
