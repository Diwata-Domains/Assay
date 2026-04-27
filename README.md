# Assay

Independent verification layer for software projects. Assay runs Playwright-based browser tests in Docker, captures screenshots and results, formats them as structured task packets, and delivers them to a Grain workflow via the ingest API.

## Requirements

- Python 3.11+
- Docker (for `assay run`)
- Node.js 18+ (for the TypeScript browser SDK)

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

## Quick Start

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

### 4. Schedule recurring runs

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

## Browser SDK

Install the TypeScript SDK in your web app:

```bash
npm install assay-sdk
```

```typescript
import { AssaySDK } from "assay-sdk";

const sdk = new AssaySDK({
  apiKey: "your-api-key",
  endpoint: "http://localhost:8000",
});

// Capture a screenshot + metadata and POST to /ingest
await sdk.capture({ comment: "Optional human note" });
```

## Docker Runner

The `assay run` command requires a pre-built Docker image containing Playwright.

### Build locally

```bash
cd runner
docker build -t assay-playwright:latest .
```

### Use a custom image

Set `docker_image` in `assay.toml`:

```toml
[runner]
docker_image = "myregistry.example.com/assay-playwright:latest"
```

Or override per-run (future flag — not yet wired in v0.1).

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

## License

MIT
