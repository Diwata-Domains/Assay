# Context: TASK-0040

`import_packets` in `assay.store.db` already accepts a list of packet dicts and bulk-upserts them. This task wires it to a CLI subcommand so users can migrate from the old on-disk JSON format to SQLite.
