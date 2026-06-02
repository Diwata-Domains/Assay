# Assay — Landscape

**Status:** CANONICAL
**Produced:** 2026-06-02
**Source:** Diwata-Infra P18-T02

---

## Competitors

Tools that overlap with what Assay does — visual regression, screenshot testing, verification, or CI-integrated testing.

| Tool | What it does | How Assay differs |
|---|---|---|
| **Percy** (BrowserStack) | Cloud-based visual testing — captures screenshots in CI, compares against approved baselines, PR comments with diffs. SaaS-only. | Percy is a hosted CI add-on. Assay is self-hosted, local-first, and has a Python CLI + Grain integration. Assay doesn't require SaaS infrastructure. |
| **Chromatic** (Storybook) | Visual and interaction testing for Storybook component libraries. CI integration, change review UI. | Chromatic is tightly coupled to Storybook. Assay is framework-agnostic — any URL, any page, any stack. Assay works outside component libraries. |
| **Playwright** (Microsoft) | Browser automation and testing framework. `page.screenshot()` for visual capture. | Playwright is the execution engine underneath Assay. Assay adds the structured output pipeline, baseline management, diff engine, dashboard, Grain integration, and scheduling layer on top. Not a competitor — a dependency. |
| **BackstopJS** | Open-source visual regression testing with config-driven test definitions. JSON/HTML reports. CLI-only, no hosted component. | BackstopJS is config-driven and CLI-only. Assay adds the hosted dashboard, browser SDK for in-app capture, Grain integration, and multi-user model (Phase 26). |
| **Cypress** | E2E testing framework with browser automation, assertions, and component testing. Cloud tier for recording. | Cypress is a full E2E test framework with assertion language. Assay is a screenshot verification layer — it captures state and generates diff evidence, not assertion-driven test suites. |
| **Storybook** | Component development environment with visual testing (via Chromatic or Storyshot plugin). | Storybook is for isolated component development. Assay tests full pages in production-like contexts. |
| **Argos** | Open-source screenshot comparison CI tool — GitHub Actions integration, PR comments. | Argos is CI-focused and GitHub-native. Assay is local-first with optional CI integration (Phase 23), hosted dashboard, scheduler, and Grain workflow bridge. |
| **Meticulous** | AI-powered regression testing — records user sessions, replays them. | Meticulous uses session recording for automated test generation. Assay uses explicit script definitions and manual baseline approval. Assay's approach is more operator-controlled and deterministic. |

---

## Inspirations

| Source | What it is | What Assay drew from it |
|---|---|---|
| **Grain** | CLI-first workflow kernel for AI-assisted development. Task packets as the unit of structured work. | Assay's output format — verification result packets — are designed to feed directly into Grain. The task packet model, packet lifecycle, and Grain bridge contract are all direct influences. |
| **Playwright** | Microsoft's browser automation framework — reliable cross-browser automation, screenshot APIs. | The execution engine for all Assay screenshot and script runs. Assay's Docker runner wraps Playwright's CLI and screenshot API. |
| **Percy's review model** | Human-in-the-loop baseline approval — see a diff, approve or reject to update the baseline. | Assay's approve/reject workflow (Phase 21) directly follows Percy's review model. The key difference: Assay's approval is stored in a local/self-hosted store, not a cloud service. |
| **BackstopJS** | CLI-driven visual regression with config files. `backstop test` → HTML report → `backstop approve`. | Inspired the `assay run --compare` → diff report → approve workflow sequence. Assay's three-command flow mirrors BackstopJS's test/report/approve pattern. |
| **Scrapy item pipelines** | Structured output contracts from each scrape stage, fed into the next stage deterministically. | Assay's output pipeline: capture → store → packet → ingest → Grain. Each stage produces a structured artifact the next stage consumes. |

---

## References

- **[Playwright docs — Screenshots](https://playwright.dev/docs/screenshots)** — the screenshot capture API and `fullPage` / clip options that Assay's Docker runner builds on.
- **[html-to-image](https://github.com/bubkoo/html-to-image)** — browser SDK screenshot library used in Phase 19 (replaced html2canvas). Better fidelity, handles SVG and pseudo-elements.
- **[pixelmatch](https://github.com/mapbox/pixelmatch)** — the pixel diff library Assay uses for the visual regression engine (Phase 21). Fast, threshold-configurable, produces diff image output.
- **[The Sentinel bridge contract (Grain v2_plan.md §11)](../../products/grain/docs/working/v2_plan.md)** — the verification result schema Assay produces and Grain ingests. Assay's output contract is defined here, not in Assay's own canonical docs.
- **[APScheduler](https://apscheduler.readthedocs.io/)** — the scheduler library used in Assay's daemon mode. Cron expression support, JSON job store.
