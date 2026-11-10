
import json
import os
import threading
from pathlib import Path

STORE_FILE = Path(__file__).resolve().parent / "processed_messages.json"
LOCK = threading.Lock()


def _load_ids() -> list[str]:
    if not STORE_FILE.exists():
        return []

    data = json.loads(STORE_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("Processed-message store must contain a JSON list.")

    return [item for item in data if isinstance(item, str)]


def is_message_new(message_id: str) -> bool:
    """Check whether a message ID has not been completed."""
    if not message_id:
        return False

    try:
        with LOCK:
            return message_id not in _load_ids()
    except (OSError, json.JSONDecodeError, ValueError):
        return False


def mark_message_if_new(message_id: str) -> bool:
    """Record a message ID if it has not already been recorded."""
    if not message_id:
        return False

    try:
        with LOCK:
            ids = _load_ids()

            if message_id in ids:
                return False

            ids.append(message_id)
            temporary_file = STORE_FILE.with_suffix(".tmp")
            temporary_file.write_text(
                json.dumps(ids[-5000:], indent=2),
                encoding="utf-8",
            )
            os.replace(temporary_file, STORE_FILE)
            return True
    except (OSError, json.JSONDecodeError, ValueError):
        return False


def mark_message_completed(message_id: str) -> bool:
    """Compatibility helper to record a completed message."""
    return mark_message_if_new(message_id)
