# Context: TASK-0041

`assay serve` starts the FastAPI ingest app. The app currently only has `POST /ingest`. This task adds `GET /` to return a dashboard page built from the SQLite store.

The `html_formatter.py` already has CSS and rendering patterns for packet tables — reuse its approach.
