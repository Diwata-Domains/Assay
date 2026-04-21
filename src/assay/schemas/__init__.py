import json
from pathlib import Path

_SCHEMA_DIR = Path(__file__).parent


def _load(name: str) -> dict[str, object]:
    result: dict[str, object] = json.loads((_SCHEMA_DIR / name).read_text())
    return result


ASSAY_PAYLOAD = _load("assay_payload.schema.json")
SDK_INGEST = _load("sdk_ingest.schema.json")
KEY_STORE = _load("key_store.schema.json")
SCHEDULE_STATE = _load("schedule_state.schema.json")
