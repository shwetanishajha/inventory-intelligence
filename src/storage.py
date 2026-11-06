
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RECORDS_FILE = PROCESSED_DIR / "extraction_results.json"
AUDIT_FILE = PROCESSED_DIR / "processing_audit.json"
REGISTRY_FILE = PROCESSED_DIR / "document_registry.json"


def load_json(path, default=None):
    """Load persisted JSON data."""
    if not path.exists():
        return default if default is not None else []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    """Save JSON safely using an atomic replacement."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    temp_path.replace(path)


def load_records():
    return load_json(RECORDS_FILE, [])


def save_records(records):
    save_json(RECORDS_FILE, records)


def load_audit():
    return load_json(AUDIT_FILE, [])


def save_audit(audit):
    save_json(AUDIT_FILE, audit)


def load_registry():
    return load_json(REGISTRY_FILE, [])


def save_registry(registry):
    save_json(REGISTRY_FILE, registry)
