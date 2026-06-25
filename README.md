# Assay

[![PyPI](https://img.shields.io/pypi/v/assay-kit)](https://pypi.org/project/assay-kit/)
[![License: AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)

**Visual verification for software projects.**

Assay captures browser screenshots, computes pixel-level diffs against approved baselines, and surfaces results through a dashboard with a before/after slider. It runs Playwright tests in Docker and delivers structured results to a Grain workflow via an ingest API.

---

## Features

- **Visual diff** — pixel-level comparison of screenshots against approved baselines; highlights regressions in red
- **Before/after slider** — side-by-side and overlay views in the dashboard
- **Baseline management** — approve or reject baseline updates per check; no silent regressions
- **Screenshot gallery** — browseable dashboard with thumbnails, check status, and diff overlays
- **Scheduled runs** — cron-based scheduling with configurable suites and targets
- **Grain integration** — ingest results directly into a Grain task packet for structured review and closure
- **Browser SDK** — TypeScript SDK for capturing screenshots and metadata from inside your app
- **Docker runner** — isolated Playwright execution with a prebuilt image

---

## Requirements

- Python 3.11+
- Docker (for `assay run`)
- Node.js 18+ (for the TypeScript browser SDK)

---

## Install

```bash
uv tool install assay-kit
```

Or with pip:

```bash
pip install assay-kit
```

Or from source:

```bash
git clone https://github.com/Diwata-Labs/Assay.git
cd Assay
pip install -e .
```

---

## Quick start

### 1. Configure

Create `assay.toml` in your project root (all fields optional — defaults shown):

```toml
[project]
name = "my-project"

[runner]
docker_image = "assay-playwright:latest"
timeout_seconds = 300

[output]
directory = "./assay-output"

[serve]
host = "127.0.0.1"
port = 8000

[keys]
store = "~/.assay/keys.json"

[schedule]
store = "~/.assay/schedules.json"
```

### 2. Run a test

```bash
assay run --target https://your-app.example.com
```

Exit codes: `0` = pass, `3` = fail, `1` = inconclusive or error.

### 3. Start the ingest server

```bash
# Create an API key first
assay key create --name ci

# Start the server
assay serve
```

### 4. Open the dashboard

Navigate to `http://localhost:8000` to see the screenshot gallery, check results, and diff views.

### 5. Schedule recurring runs

```bash
# Add a schedule (standard 5-field cron)
assay schedule add --cron "0 8 * * *" --suite smoke --target https://your-app.example.com

# List schedules
assay schedule list

# Start the scheduler (foreground; Ctrl+C to stop)
assay schedule run

# Remove a schedule
assay schedule remove <id>
```

---

## Dashboard

The Assay dashboard (`assay serve`) provides:

- **Screenshot gallery** — thumbnails for every captured check, sorted by run
- **Check results** — pass/fail/inconclusive status per check with diff metadata
- **Visual diff viewer** — side-by-side before/after comparison with a draggable overlay slider
- **Baseline management** — approve a new baseline or reject and keep the existing one per check

Baselines are stored locally alongside your output directory. Approving a baseline makes it the reference for future runs.

---

## Grain integration

Assay results can be ingested directly into a [Grain](https://github.com/Diwata-Labs/Grain) task packet for structured review before closure.

The ingest API is protected by API key auth. Create a key before starting the server:

```bash
assay key create --name grain
assay key list
```

The ingest endpoint accepts structured payloads from the browser SDK or from `assay run`. Grain reads the result via:

```bash
grain verify submit --id TASK-0001
grain verify status --verification-id VERIFY-0001-001
```

---

## Browser SDK

> The browser SDK is for **human/in-app capture from a real browser**. It is **not** the
> agent path — its `capture()` reads the live DOM and throws outside a browser. Agents should
> use the CLI, `POST /ingest`, or MCP (see [Agent / programmatic access](#agent--programmatic-access)).

Install the TypeScript SDK in your web app:

```bash
npm install @diwata-labs/assay-sdk
```

```typescript
import { AssaySDK } from "@diwata-labs/assay-sdk";

const sdk = new AssaySDK({
  apiKey: "your-api-key",
  endpoint: "http://localhost:8000",
});

// Capture a screenshot and metadata, POST to /ingest
await sdk.capture({ comment: "Optional human note" });
```

The SDK captures the current viewport, serializes metadata, and POSTs to the ingest endpoint. Results appear in the dashboard immediately.

---

## Agent / programmatic access

Assay is fully familiar-drivable: an agent can run the entire verification loop headlessly,
with no browser and no dashboard. **Agents use the CLI, `POST /ingest`, or the MCP server —
never the browser SDK** (its `capture()` is DOM-locked and throws in Node).

The machine-readable contract — every tool, its JSON Schema, and the HTTP endpoints — lives at
`src/assay/contracts/tool_manifest.json` and is served at `GET /mcp/manifest`. Treat that as
the source of truth.

### Three agent surfaces

1. **CLI** — the most complete surface. Every agent-relevant command takes `--format json`:

   ```bash
   assay init --non-interactive --admin-email a@b.com --admin-password "$PW" --format json
   assay run --target https://app.example.com --task-id TASK-0001 --format json
   assay check --format json
   assay key create --name agent --format json
   assay baseline approve VERIFY-0001-001 --format json
   assay baseline list --format json
   ```

   `assay init --non-interactive` (alias `--yes`) never prompts or reads a TTY — pass the
   admin email/password as flags or via `ASSAY_ADMIN_EMAIL` / `ASSAY_ADMIN_PASSWORD` for
   zero-touch setup.

2. **`POST /ingest`** — submit a captured screenshot payload directly. Authenticated with the
   `X-Assay-Key` header. The request body conforms to the JSON Schema
   [`src/assay/schemas/sdk_ingest.schema.json`](src/assay/schemas/sdk_ingest.schema.json); the
   stored result conforms to
   [`src/assay/schemas/assay_payload.schema.json`](src/assay/schemas/assay_payload.schema.json).

3. **MCP server** — `GET /mcp/tools`, `GET /mcp/manifest`, `POST /mcp/call`. All `/mcp/*` and
   `/baselines*` routes require a valid API key (`X-Assay-Key`). The tools cover the full loop:

   | tool | purpose |
   |------|---------|
   | `run_verification` | trigger a real run; returns `verification_id` + outcome + diff |
   | `get_report` | structured report for a `verification_id` |
   | `get_status` | poll a `verification_id` (`pending` / `complete`) |
   | `list_runs` | list runs, filter by `task_id` / `outcome` |
   | `list_baselines` | list set baselines |
   | `approve_baseline` / `reject_baseline` / `set_baseline` | drive the baseline workflow |

   ```bash
   KEY=$(assay key create --name agent --format json | tail -1 | python -c 'import sys,json;print(json.load(sys.stdin)["key"])')

   curl -s localhost:8000/mcp/call -H "X-Assay-Key: $KEY" \
     -d '{"tool":"run_verification","input":{"target":"https://app.example.com"}}'

   curl -s localhost:8000/mcp/call -H "X-Assay-Key: $KEY" \
     -d '{"tool":"approve_baseline","input":{"verification_id":"VERIFY-0001-001"}}'
   ```

Baselines are also manageable headlessly over API-key HTTP: `GET /baselines`,
`POST /baselines/set|approve|reject` (body `{"verification_id": "..."}`) — no dashboard needed.

---

## Docker runner

The `assay run` command requires a pre-built Docker image containing Playwright.

### Build locally

```bash
cd runner
docker build -t assay-playwright:latest .
```

### Use a custom image

```toml
[runner]
docker_image = "myregistry.example.com/assay-playwright:latest"
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/assay
```

---

## License

[AGPL-3.0-only](LICENSE). Commercial licensing for closed-source or hosted use: ss@diwata.domains
