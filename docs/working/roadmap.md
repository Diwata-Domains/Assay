# Assay — Future Roadmap

**Produced:** 2026-06-02
**Source:** Diwata-Infra P18-T03

Items here are not committed or scheduled. They become phases when current work stabilizes and demand is clear.

---

## Strong Candidates

Features with clear demand or obvious next steps after the current phase sequence (22–26).

**Security verification (pre-pentesting layer)**
Once Phase 25 (functional + integration checks) is stable, extend the check engine with a dedicated security check type: verify that auth is enforced on all protected routes, that sensitive data isn't exposed in error responses, that security headers (CSP, HSTS, X-Content-Type-Options) are present, and that rate limiting is active. This is NOT active exploitation — it's verifying that the security posture is correctly configured. Prerequisite for any enterprise client delivery or SOC 2 preparation. Target: after Diwa Domains has paying customers and before any enterprise sales push.

**Active penetration testing integration**
Full exploit-attempt security testing — OWASP scanning, injection probes, auth bypass attempts. This is a separate specialized domain and would most likely be an integration with an existing engine (OWASP ZAP, Nuclei) rather than a built-from-scratch tool. Requires the security verification layer (above) to be stable first, and requires a clear operator consent model (active probing against production is destructive if misconfigured). Timing: post-Diwa Domains enterprise tier, or as a standalone "Probe" product under the Diwata toolkit.

**Multi-browser support**
Assay currently runs Chromium only via Playwright. Adding Firefox and WebKit would cover the full Playwright browser matrix. Requires updating the Docker runner and result packet to tag browser type. Natural extension after Phase 22 (script runner) and Phase 24 (multi-viewport) prove the multi-dimension test model.

**Python server-side SDK**
The browser SDK captures in-app screenshots from the frontend. A Python SDK equivalent would let backend or server-side test suites submit verification packets directly without CLI invocation. Follows the same ingest endpoint contract. Target: FastAPI/Flask/Django project verification flows.

**Public share links for verification reports**
Allow a verification report to be shared via a public URL with no login required (time-limited, read-only). Requires Phase 26 org model first (so the share is scoped to the correct org's data). Relevant for freelance/agency workflows where clients need to view verification results without a full account.

**Video capture on failure**
When a step-based script (Phase 22) fails, capture a short video of the browser session leading up to the failure. Playwright supports `recordVideo`. Adds significant diagnostic value for intermittent failures.

**Conclave integration**
Assay as a tool a Conclave Familiar can invoke — the Familiar sends verification requests to Assay and surfaces results back to the operator. Requires the Grain ↔ Assay ↔ toolkit contract (Grain P30-T02) to stabilize first.

---

## Under Consideration

Directions being evaluated. May not ship.

**Hosted SaaS tier**
A cloud-hosted Assay instance — no VPS required, sign up and start running. Billing per verification run or per org. Phase 26 (multi-user) is the prerequisite. Requires a decision about whether Assay becomes a standalone SaaS product or remains a self-hosted tool with an optional hosted tier.

**Diff threshold configuration per URL**
Different pages tolerate different levels of visual change (e.g. a dynamic dashboard vs a static marketing page). Per-URL diff thresholds in `assay.toml` rather than a single global setting. Not a blocker for Phase 22–25 but useful before the CI integration (Phase 23) is widely adopted.

**Cross-browser baseline comparison**
One baseline per browser type, so a page can be approved at different states across Chrome, Firefox, and Safari. Requires multi-browser support first.

**Slack/Teams rich cards**
Phase 25 covers webhooks + Slack integration. A richer alternative: Slack block kit cards with inline diff thumbnails instead of plain JSON payloads.

---

## Explicitly Deferred

Things considered and intentionally not scheduled.

**OAuth / SSO** — Deferred from v1 scope. Phase 26 builds basic email/password multi-user. OAuth is Phase 26+.
**Keychain storage for API keys** — Deferred from Q6. v1 uses bcrypt + plaintext JSON file. Acceptable until the hosted tier requires stronger storage.
**CDN distribution for browser SDK** — npm is the only distribution path for v1. CDN build deferred until npm adoption is confirmed.
**Windows scheduler support** — `assay schedule start` uses `os.fork()` (POSIX only). Refactoring to a cross-platform daemon process is deferred until Windows support is explicitly requested.
**AI-generated test scripts** — Recording user sessions or generating scripts from natural language descriptions. Depends on script format (Phase 22) being stable first. Not before Phase 24+ at earliest.

---

## Not on the Roadmap

Hard non-goals:

- **GUI desktop app** — Assay's operator surface is the dashboard (web) and CLI. No desktop app planned.
- **Replacing Playwright** — Assay wraps Playwright. The execution engine is not being rebuilt.
- **Full test suite replacement** — Assay is a verification layer, not a replacement for unit/integration tests. It does not generate assertions. It captures and compares visual state.
- **Assay replacing Grain** — Assay is a sibling tool to Grain, not a workflow system. It produces structured packets that Grain can consume, but does not manage task lifecycle, phases, or operator workflow.
