import sqlite3
import sys
from pathlib import Path


ALLOWED_STATUSES = (
    "processing",
    "prepared",
    "sent",
    "failed",
    "uncertain",
)


def migrate_database(db_path: Path) -> None:
    db_path = db_path.resolve()

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    connection = sqlite3.connect(db_path, timeout=10)

    try:
        connection.execute("PRAGMA busy_timeout = 10000")

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Database integrity check failed: {integrity}"
            )

        connection.execute("BEGIN IMMEDIATE")

        table = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'message_state'
            """
        ).fetchone()

        if table is None:
            raise RuntimeError("message_state table was not found")

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(message_state)"
            )
        }

        required_columns = {
            "message_id",
            "status",
            "updated_at",
            "reply_text",
            "last_error",
        }

        if not required_columns.issubset(columns):
            raise RuntimeError(
                "Unexpected database columns; migration stopped"
            )

        rows_before = connection.execute(
            """
            SELECT message_id, status, updated_at, reply_text, last_error
            FROM message_state
            ORDER BY message_id
            """
        ).fetchall()

        for row in rows_before:
            if row[1] not in ALLOWED_STATUSES:
                raise RuntimeError(
                    f"Unsupported status found for a record; migration stopped"
                )

        old_sql = table[0] or ""

        if "'prepared'" in old_sql:
            print("Migration not needed: prepared status is already supported.")
            connection.rollback()
            return

        connection.execute(
            """
            CREATE TABLE message_state_new (
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

        connection.executemany(
            """
            INSERT INTO message_state_new
                (message_id, status, updated_at, reply_text, last_error)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows_before,
        )

        connection.execute("DROP TABLE message_state")
        connection.execute(
            "ALTER TABLE message_state_new RENAME TO message_state"
        )

        rows_after = connection.execute(
            """
            SELECT message_id, status, updated_at, reply_text, last_error
            FROM message_state
            ORDER BY message_id
            """
        ).fetchall()

        if rows_after != rows_before:
            raise RuntimeError(
                "Record comparison failed; migration rolled back"
            )

        connection.commit()

        integrity_after = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity_after != "ok":
            raise RuntimeError(
                f"Post-migration integrity check failed: {integrity_after}"
            )

        print("MIGRATION PASSED")
        print(f"Database: {db_path.name}")
        print(f"Records preserved: {len(rows_after)}")
        print("Existing record contents preserved: Yes")
        print("Prepared status supported: Yes")
        print("WhatsApp message sent: No")

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python migrate_message_state_db.py "
            "<database_path>"
        )
        sys.exit(2)

    migrate_database(Path(sys.argv[1]))