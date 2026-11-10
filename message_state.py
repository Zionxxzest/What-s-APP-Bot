import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "message_state.sqlite3"
BUSY_TIMEOUT_SECONDS = 10

ALLOWED_STATUSES = {
    "processing",
    "prepared",
    "sent",
    "failed",
    "uncertain",
}

TRANSITIONS = {
    "processing": {"prepared", "failed", "uncertain"},
    "prepared": {"sent", "failed", "uncertain"},
    "sent": set(),
    "failed": set(),
    "uncertain": set(),
}


@contextmanager
def _connect():
    """Open a database connection and always close it."""
    connection = sqlite3.connect(
        DB_FILE,
        timeout=BUSY_TIMEOUT_SECONDS,
    )
    try:
        connection.execute("PRAGMA busy_timeout = 10000")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_table(connection):
    """Create the new-schema table if it does not already exist."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS message_state (
            message_id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK (
                status IN (
                    'processing',
                    'prepared',
                    'sent',
                    'failed',
                    'uncertain'
                )
            ),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reply_text TEXT,
            last_error TEXT
        )
        """
    )


def claim_message(message_id: str) -> bool:
    """Claim an incoming message ID once; never reclaim existing IDs."""
    if not isinstance(message_id, str) or not message_id.strip():
        return False

    try:
        with _connect() as connection:
            _ensure_table(connection)
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO message_state (message_id, status)
                VALUES (?, 'processing')
                """,
                (message_id,),
            )
            return cursor.rowcount == 1
    except sqlite3.Error:
        return False


def save_prepared_reply(message_id: str, reply_text: str) -> bool:
    """Save a reply and atomically move processing to prepared."""
    if (
        not isinstance(message_id, str)
        or not message_id.strip()
        or not isinstance(reply_text, str)
        or not reply_text.strip()
    ):
        return False

    try:
        with _connect() as connection:
            _ensure_table(connection)
            cursor = connection.execute(
                """
                UPDATE message_state
                SET status = 'prepared',
                    reply_text = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    last_error = NULL
                WHERE message_id = ?
                  AND status = 'processing'
                """,
                (reply_text, message_id),
            )
            return cursor.rowcount == 1
    except sqlite3.Error:
        return False


def set_message_status(
    message_id: str,
    status: str,
    error: str | None = None,
) -> bool:
    """Apply only permitted transitions; never reopen terminal states."""
    if (
        not isinstance(message_id, str)
        or not message_id.strip()
        or status not in ALLOWED_STATUSES
    ):
        return False

    try:
        with _connect() as connection:
            _ensure_table(connection)

            row = connection.execute(
                "SELECT status FROM message_state WHERE message_id = ?",
                (message_id,),
            ).fetchone()

            if not row:
                return False

            current_status = row[0]
            if status not in TRANSITIONS[current_status]:
                return False

            cursor = connection.execute(
                """
                UPDATE message_state
                SET status = ?,
                    last_error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
                  AND status = ?
                """,
                (status, error, message_id, current_status),
            )
            return cursor.rowcount == 1
    except sqlite3.Error:
        return False


def get_message_status(message_id: str) -> str | None:
    """Return a message's status, or None if it is unknown."""
    if not isinstance(message_id, str) or not message_id.strip():
        return None

    try:
        with _connect() as connection:
            _ensure_table(connection)
            row = connection.execute(
                "SELECT status FROM message_state WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            return row[0] if row else None
    except sqlite3.Error:
        return None