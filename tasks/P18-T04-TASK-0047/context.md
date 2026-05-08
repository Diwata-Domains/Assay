# Context: TASK-0047

`_do_submit` in `cli/main.py` copies the packet to grain's output path after schema validation. The verification_id in the packet comes from `format_packet` — it's a UUID unless `--verification-id` was passed. A simple regex check (`re.match(r'^[0-9a-f-]{36}$', vid)`) identifies UUID-shaped IDs.
