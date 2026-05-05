# Context: TASK-0043

Dashboard rows already link to `/packet/{verification_id}`. This task implements that route. `list_packets` returns all packets; filter by `verification_id` key. Screenshot inline uses `base64.b64encode(Path(ref).read_bytes()).decode()` — same pattern as `html_formatter.py`.
