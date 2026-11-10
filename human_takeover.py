
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from dotenv import dotenv_values


DB_FILE = Path(__file__).resolve().parent / "message_state.sqlite3"
ENV_FILE = Path(__file__).resolve().parent / ".env"


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to digits for consistent comparison."""
    if not isinstance(phone, str):
        return ""
    return "".join(ch for ch in phone if ch.isdigit())


def _connect():
    """Create the takeover table without changing existing message records."""
    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS human_takeover (
            customer_phone TEXT PRIMARY KEY,
            active INTEGER NOT NULL CHECK (active IN (0, 1)),
            reason TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL DEFAULT ''
        )
    """)
    connection.commit()
    return connection


def activate_takeover(
    customer_phone: str,
    reason: str = "Human assistance requested",
    updated_by: str = "system",
) -> bool:
    """Persistently pause AI handling for one customer."""
    phone = normalize_phone(customer_phone)
    if not phone:
        return False

    connection = _connect()
    try:
        connection.execute("""
            INSERT INTO human_takeover
                (customer_phone, active, reason, updated_at, updated_by)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(customer_phone) DO UPDATE SET
                active = 1,
                reason = excluded.reason,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
        """, (
            phone,
            str(reason)[:500],
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            str(updated_by)[:100],
        ))
        connection.commit()
        return True
    finally:
        connection.close()


def is_takeover_active(customer_phone: str) -> bool:
    """Return True when a customer is currently in human-takeover mode."""
    phone = normalize_phone(customer_phone)
    if not phone:
        return False

    connection = _connect()
    try:
        row = connection.execute("""
            SELECT active
            FROM human_takeover
            WHERE customer_phone = ?
        """, (phone,)).fetchone()
        return bool(row and row[0] == 1)
    finally:
        connection.close()


def resume_customer(customer_phone: str, staff_phone: str) -> bool:
    """Resume AI handling only when the configured staff number requests it."""
    settings = dotenv_values(ENV_FILE)
    authorized_phone = normalize_phone(
        settings.get("AUTHORIZED_STAFF_PHONE", "")
    )

    requester = normalize_phone(staff_phone)
    customer = normalize_phone(customer_phone)

    # Fail closed if the authorized staff number is not configured.
    if not authorized_phone or requester != authorized_phone or not customer:
        return False

    connection = _connect()
    try:
        cursor = connection.execute("""
            UPDATE human_takeover
            SET active = 0,
                updated_at = ?,
                updated_by = ?
            WHERE customer_phone = ? AND active = 1
        """, (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            requester,
            customer,
        ))
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()
