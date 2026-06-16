# Context: TASK-0048

Grain's `_validate_ingest_payload` checks: required fields (verification_id, task_id, issue_type, severity, outcome, summary), issue_type whitelist, severity whitelist, outcome whitelist. The test imports this function directly from grain (if available) or reimplements the same checks to stay independent.
