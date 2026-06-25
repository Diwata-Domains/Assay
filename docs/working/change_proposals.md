# Change Proposals

---

## CP-001 — Replace Grain task packet schema in `data_contracts.md` §1

**Status:** applied (2026-04-15)
**Proposed by:** P1-T03-TASK-0003
**Affects:** `docs/canonical/data_contracts.md` §1
**Requires:** human approval per `PROJECT_RULES.md` §3

---

### Finding

Q1 is resolved. Grain has an existing, documented output contract that Assay must conform to.

Grain's `docs/working/v2_plan.md §11.2` defines the **Sentinel result payload schema** — the exact JSON structure Assay must produce and deliver to Grain via `grain verify ingest --payload <path>`. Assay was formerly called Sentinel; this contract was written for Assay.

The current schema in `data_contracts.md §1` is a freeform bug/test ticket format that does not match Grain's contract. It must be replaced.

---

### Current schema (data_contracts.md §1) — INCORRECT

```json
{
  "id": "<uuid-v4>",
  "schema_version": "1.0.0",
  "created_at": "<ISO 8601>",
  "source": "assay",
  "source_version": "<semver>",
  "project": "<project-name>",
  "type": "test_failure | bug_report | verification",
  "status": "ready",
  "title": "<short description>",
  "description": "<full description>",
  "severity": "low | medium | high | critical",
  "artifacts": [...],
  "metadata": {...},
  "user_comment": "<optional>"
}
```

---

### Proposed schema — Grain Sentinel result payload contract

**Required fields:**

```json
{
  "verification_id": "<string — stable ID assigned by Assay at submission>",
  "task_id": "<string — the Grain task packet ID being verified, e.g. TASK-0070>",
  "issue_type": "<enum: test_failure | bug_finding | screenshot_evidence | trace_capture | human_annotation>",
  "severity": "<enum: info | warning | error | critical>",
  "outcome": "<enum: pass | fail | inconclusive>",
  "summary": "<string — human-readable description of the finding>"
}
```

**Optional fields:**

```json
{
  "artifact_refs": ["<path or URI to captured artifact>"],
  "followup_candidates": [
    { "title": "<string>", "description": "<string>" }
  ],
  "verified_at": "<ISO 8601 datetime>"
}
```

---

### Delivery model

Assay writes the payload as a JSON file to a Grain-visible location (or a configured output directory). The Grain operator runs:

```
grain verify ingest --verification-id <id> --payload <path>
```

Assay does not push directly to Grain. Grain pulls via operator action.

---

### Implications for architecture

- The `task_id` field means Assay verifications are tied to specific Grain task packets — Assay is not a standalone bug tracker but a verification service for Grain workflows.
- `followup_candidates` are proposals for the operator, not auto-created packets. Assay should populate this when tests or captures identify likely follow-up work.
- The browser SDK captures (`screenshot_evidence`, `human_annotation`) and runner results (`test_failure`, `bug_finding`) map cleanly to `issue_type` values.
- Severity mapping: Playwright test failures → `error` or `critical`; SDK captures default to `info` unless user marks otherwise.

---

### Proposed update to data_contracts.md §1

Replace the current §1 content with the Grain-conformant schema above. Add a note that this schema is defined by Grain's bridge contract (`v2_plan.md §11`) and Assay must not deviate from required fields.

---

### Architectural open question surfaced by this finding

The `task_id` field assumes every Assay output references a specific Grain task packet. This works for the bug bounty / verification use case, but raises a question for standalone CLI use (e.g., `assay run` against a project that has no Grain workflow). Options:

- A) `task_id` is required — Assay only operates within Grain workflows
- B) `task_id` is optional — standalone mode produces payloads without it; Grain ingestion requires it
- C) Assay has two output modes: Grain payload (with `task_id`) and standalone summary (without)

**Recommendation:** Option B — `task_id` optional for standalone runs. Grain's contract requires it for ingestion, but Assay should support standalone use per its stated scope. Log as Q10 in open_questions.md.

---

### Decision needed from

Project owner — approve, reject, or amend before P1-T04 begins.

---

## CP-002 — Rename "Sentinel" references in `data_contracts.md` §1 and schema files

**Status:** applied (2026-04-16)
**Proposed by:** Phase 4 review
**Affects:** `docs/canonical/data_contracts.md` §1, `src/assay/schemas/sentinel_payload.schema.json`
**Requires:** human approval per `PROJECT_RULES.md` §3

---

### Finding

`data_contracts.md §1` is titled "Grain Sentinel Result Payload Schema" and describes a delivery model using `grain verify ingest --payload <path>`. Both are stale:

1. **"Sentinel" was Grain's internal name** for the verification layer feature before it was extracted into this standalone tool, Assay. The schema was written for Assay; the name should reflect that.
2. **`grain verify ingest` does not exist** in the current Grain CLI. The command was planned in `grain/docs/working/v2_plan.md §11.2` but never shipped — because the feature became Assay instead.
3. **`sentinel_payload.schema.json`** carries the same stale name.

---

### Proposed changes

**`docs/canonical/data_contracts.md` §1:**
- Rename heading: `"Grain Sentinel Result Payload Schema"` → `"Assay Result Payload Schema"`
- Remove the `grain verify ingest` command from the delivery model section
- Replace delivery model with: *"Assay writes the payload JSON to the configured output directory. The operator may inspect it directly or integrate it into their workflow via `assay report` or by reading the file."*
- Remove the reference to `grain/docs/working/v2_plan.md §11.2` as the defining authority (Assay itself is now the authority)

**`src/assay/schemas/sentinel_payload.schema.json`:**
- Rename file to `assay_payload.schema.json`
- Update `"$id"` from `"assay:sentinel_payload"` to `"assay:payload"`
- Update `"title"` from `"Sentinel Result Payload"` to `"Assay Result Payload"`

**`src/assay/schemas/__init__.py`:**
- Update `SENTINEL_PAYLOAD = _load("sentinel_payload.schema.json")` → `ASSAY_PAYLOAD = _load("assay_payload.schema.json")`

**All references in tests and source:**
- Update `SENTINEL_PAYLOAD` → `ASSAY_PAYLOAD` in `tests/test_schemas.py` and `tests/test_packet_schema.py`

---

### What does NOT change

- The payload JSON structure (required and optional fields) is unchanged
- The `$schema` draft version is unchanged
- No data format changes — only naming

---

### Decision needed from

Project owner — approve to apply in Phase 5 or as a standalone patch.

---

## CP-003 — Add `assay schedule run` to CLI spec in `data_contracts.md §5`

**Status:** applied (2026-04-21)
**Proposed by:** P7-T04-TASK-0004
**Affects:** `docs/canonical/data_contracts.md` §5 (Configuration File Schema / CLI surface)
**Requires:** human approval per `PROJECT_RULES.md` §3

---

### Finding

P7-T04 implemented `assay schedule run` — a foreground scheduler loop that fires registered schedules via APScheduler. This command was not present in the original CLI specification in `data_contracts.md`.

### Proposed addition to `data_contracts.md §5` CLI commands table

```
assay schedule run    Start the foreground scheduler loop (runs until Ctrl+C)
```

### What does NOT change

- Existing CLI commands and their signatures are unchanged
- Schedule store schema (§4) is unchanged
- No behavioral changes to add/list/remove

---

### Decision needed from

Project owner — approve to update `data_contracts.md §5` with the new command.

---

## CP-004 — Refresh canonical `product_scope.md` to the shipped surface (dashboard + auth are no longer non-goals)

**Status:** proposed (2026-06-25)
**Proposed by:** Phase 28 documentation reconciliation (P28-T04)
**Affects:** `docs/canonical/product_scope.md` §3 (Non-Goals), §5 (Key Capabilities), §6 (Scope Boundaries), §8 (Monetization)
**Requires:** human approval per canonical-doc rule (`CLAUDE.md` §Canonical Docs)

---

### Finding

`docs/canonical/product_scope.md` is frozen at the v1 framing and now contradicts the
shipped product. It still lists capabilities that have been implemented and released (or are
implemented and pending the v0.3.0 release) as **v1 NON-goals / deferred to v2**:

- §3 Non-Goals (v1) lists **"Web UI or dashboard"** and **"Multi-user account management"**
  and **"OAuth / SSO authentication"** as non-goals.
- §6 "Explicitly deferred to v2" repeats **"Web UI / dashboard"**, **"Multi-user accounts"**,
  and **"OAuth / SSO / advanced auth"**.

On-disk reality (Phases 17–27, archived under `tasks/archive/`):

- **Web UI / dashboard SHIPPED** — Phase 17 (Web UI / Dashboard), Phase 18 (diff engine +
  before/after slider in dashboard), Phase 19 (baseline approve/reject in dashboard).
- **Admin auth SHIPPED** — the hosted dashboard ships single-admin auth + API key management
  UI (JWT-protected admin endpoints; see `project_state.md` and the backlog v0.3.0 ledger).
- Multi-user / org accounts and full OAuth/SSO remain genuinely future work (the client
  access layer is planned in v0.4.0 backlog Phase 31), so those specific items can stay
  deferred — but the blanket "no dashboard / no auth" framing is wrong.

Agents and operators reading the canonical scope are being told the dashboard and auth are
out of scope while the code, the dashboard routes, and the auth module all exist.

---

### Proposed changes to `product_scope.md`

**§3 Non-Goals (v1):**
- REMOVE "Web UI or dashboard" (shipped, Phase 17).
- REMOVE "OAuth / SSO authentication" as an absolute non-goal; reframe as: *"Multi-tenant
  OAuth / SSO — deferred; v0.3.0 ships single-admin auth + API-key auth only."*
- KEEP "Bug bounty public portal", "SaaS deployment / hosted infrastructure" as non-goals.
- Reframe "Multi-user account management" → *"Multi-user / org accounts — planned for v0.4.0
  (client access layer, backlog Phase 31), not in v0.3.0."*

**§5 Key Capabilities:** ADD the shipped surface:
- Self-hosted **web dashboard** (packet history, packet detail, before/after diff slider,
  baseline approve/reject).
- **Visual regression**: baseline capture, pixel-diff engine, `assay run --compare`.
- **Single-admin auth** (JWT) + API-key management UI on the hosted dashboard.
- **Check library** (HTTP / header / auth checks) and **JSON Script DSL** (`assay run --script`).
- **CI integration**: GitHub Action with non-zero exit on regression + commit-status posting.
- **Multi-viewport** capture/diff.

**§6 Scope Boundaries:** move dashboard + single-admin auth from "deferred to v2" into "in
scope (shipped in v0.3.0)"; keep org accounts / OAuth-SSO / SaaS hosting deferred.

**§8 Monetization:** note that admin auth + per-project API keys are now in place as the auth
surface; usage/subscription billing still deferred.

---

### What does NOT change

- Assay's core identity as an independent verification layer with no hard Grain dependency (§1, §7).
- The standalone-first posture (Docker required; local filesystem output).
- Genuinely-future items: org/multi-tenant accounts, full OAuth/SSO, SaaS hosting, public
  bug-bounty portal remain non-goals / deferred.

---

### Decision needed from

Project owner — approve, reject, or amend. On approval, apply the edits directly to
`docs/canonical/product_scope.md` and mark this proposal `applied`.

---

## CP-005 — Add `code_review` issue_type + optional `review` block to the Assay payload contract

**Status:** proposed (2026-06-25)
**Proposed by:** Phase 30 — Adversarial AI Code Review (P30-T02)
**Affects:** `docs/canonical/data_contracts.md` §1, `src/assay/schemas/assay_payload.schema.json`
**Requires:** human approval per canonical-doc rule (`CLAUDE.md` §Canonical Docs)
**Cross-product note:** Grain's `_validate_ingest_payload`
(`products/grain/src/grain/services/verification_service.py`) hard-codes the same `issue_type`
enum. The new value below is non-ingestable on the Grain side until Grain's validator is
extended in lockstep — so this CP must be approved and applied on **both** products together.

---

### Finding

Phase 30 introduces adversarial / multi-agent AI **code review** as a new verification MODE
(memory: `assay-vnext-adversarial-review`). Its verdict (`approved` / `needs_fix`) flows back
to Grain as a packet `outcome` and populates `grain review`. The verdict carries structured
findings (per-file/line severity + message) and reviewer/judge provenance that the current
frozen payload schema has nowhere to put:

- `issue_type` enum is `test_failure | bug_finding | screenshot_evidence | trace_capture |
  human_annotation` — none of these names a code review.
- The schema is `additionalProperties: false`, so a structured `review` block cannot be
  attached without a schema edit.

Until this CP lands, code_review packets stay schema-valid by reusing `issue_type:
"bug_finding"` and folding findings into `summary` + `artifact_refs` (the runner persists the
full findings list + transcripts as artifacts). The in-code `CodeReviewResult` domain type
already carries the structured verdict; this CP only asks to surface it in the wire contract.

---

### Proposed changes

**(a) `issue_type` enum — add `code_review`:**

```
issue_type: test_failure | bug_finding | screenshot_evidence | trace_capture
          | human_annotation | code_review
```

Apply in BOTH:
- `docs/canonical/data_contracts.md` §1 (Required fields block + the `issue_type` field rule).
- `src/assay/schemas/assay_payload.schema.json` `properties.issue_type.enum`.
- (lockstep) Grain `_validate_ingest_payload` allowed set + its error message.

**(b) Optional `review` block** — additive, non-required, backward-compatible:

```json
{
  "review": {
    "verdict": "<enum: pass | fail | inconclusive>",
    "findings": [
      {
        "file": "<string — repo-relative path>",
        "line": "<integer — 1-based; 0 or null for file-level>",
        "severity": "<enum: info | warning | error | critical>",
        "message": "<string>"
      }
    ],
    "reviewers": ["<string — reviewer/agent identifier, e.g. proposer, critic, judge>"],
    "confidence": "<number — 0.0..1.0>"
  }
}
```

Schema fragment to add under `properties` (keeping `additionalProperties: false` at the top
level — `review` becomes a known property):

```json
"review": {
  "type": ["object", "null"],
  "additionalProperties": false,
  "required": ["verdict"],
  "properties": {
    "verdict": { "type": "string", "enum": ["pass", "fail", "inconclusive"] },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["file", "severity", "message"],
        "properties": {
          "file": { "type": "string", "minLength": 1 },
          "line": { "type": ["integer", "null"] },
          "severity": { "type": "string", "enum": ["info", "warning", "error", "critical"] },
          "message": { "type": "string", "minLength": 1 }
        }
      }
    },
    "reviewers": { "type": "array", "items": { "type": "string", "minLength": 1 } },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

---

### Verdict → outcome mapping (records the intent; already implemented in code)

| review.verdict | packet outcome | grain review verdict |
|----------------|----------------|----------------------|
| `pass`         | `pass`         | `approved`           |
| `fail`         | `fail`         | `needs_fix`          |
| `inconclusive` | `inconclusive` | `needs_human`        |

This mapping is implemented in `src/assay/review/verdict.py` against the EXISTING schema and
does not require this CP — the CP only governs the wire-level `code_review` issue_type and the
`review` block.

---

### What does NOT change

- All current required fields and their types are unchanged.
- The `pass | fail | inconclusive` `outcome` enum is unchanged (the verdict reuses it).
- The `severity` enum is unchanged (findings reuse `info | warning | error | critical`).
- `additionalProperties: false` is preserved; `review` is added as a known optional property.
- Until applied, code_review packets emit `issue_type: "bug_finding"` and omit `review`, so
  they remain valid against the current frozen schema AND the current Grain validator.

---

### Decision needed from

Project owner — approve, reject, or amend. On approval, apply the schema + `data_contracts.md`
edits AND the lockstep Grain validator edit, flip `format_review_packet` to emit
`issue_type: "code_review"` + the `review` block, and mark this proposal `applied`.
