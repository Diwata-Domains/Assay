# Context: TASK-0045

`format_packet` in `formatter/formatter.py` generates a UUID for `verification_id`. Need to accept an optional override. The CLI `run` command calls `format_packet(bundle, task_id=...)` — add `verification_id=` kwarg. The ingest app's `format_sdk_packet` similarly generates a UUID; accept override via `payload.metadata["verification_id"]`.
