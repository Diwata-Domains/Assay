# Security Policy

## Supported Versions

Only the latest released version of assay-kit receives security fixes.

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |
| Older   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities by email to: **ss@diwata.domains**

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- The version of assay-kit affected
- Any suggested mitigations if known

You can expect an acknowledgement within **5 business days** and a resolution update within **30 days** for confirmed issues.

We will credit reporters in the release notes unless you prefer to remain anonymous.

## Scope

Assay has two surfaces with distinct security profiles:

**`assay serve` (HTTP server)**
- Admin authentication via JWT — issues most relevant here include auth bypass, token forgery, and session fixation
- API key authentication on `/ingest` — issues include key leakage via logs, timing attacks on key comparison, and unauthorized ingest
- Screenshot storage — path traversal in artifact file writes
- SQLite database — injection via unvalidated query parameters

**`assay run` (Docker runner)**
- Runs Playwright inside a Docker container — issues include container escape and unsafe handling of the target URL
- Output directory writes — path traversal in artifact paths returned from the runner

**`assay-sdk` (TypeScript browser SDK)**
- Sends screenshots and metadata to the ingest endpoint — issues include SSRF if the endpoint is user-controlled

## Disclosure Policy

We follow coordinated disclosure. Once a fix is available, we will publish a security advisory on GitHub and note the fix in the changelog.
