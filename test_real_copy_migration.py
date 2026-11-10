import sqlite3
from pathlib import Path

DB_FILE = Path(
    r"C:\WhatsAppAutomation\message_state.migration_test_20261025_180929.sqlite3"
)


def main():
    connection = sqlite3.connect(DB_FILE)

    try:
        connection.execute("PRAGMA busy_timeout = 10000")

        original_rows = connection.execute(
            """
            SELECT message_id, status, updated_at, reply_text, last_error
            FROM message_state
            ORDER BY message_id
            """
        ).fetchall()

        assert len(original_rows) == 16, (
            f"Expected 16 records, found {len(original_rows)}"
        )

        connection.execute("BEGIN IMMEDIATE")

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

        connection.execute(
            """
            INSERT INTO message_state_new (
                message_id, status, updated_at, reply_text, last_error
            )
            SELECT
                message_id, status, updated_at, reply_text, last_error
            FROM message_state
            """
        )

        copied_rows = connection.execute(
            """
            SELECT message_id, status, updated_at, reply_text, last_error
            FROM message_state_new
            ORDER BY message_id
            """
        ).fetchall()

        assert copied_rows == original_rows, (
            "Existing records differ in the replacement table"
        )

        connection.execute("DROP TABLE message_state")
        connection.execute(
            "ALTER TABLE message_state_new RENAME TO message_state"
        )
        connection.commit()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        migrated_rows = connection.execute(
            """
            SELECT message_id, status, updated_at, reply_text, last_error
            FROM message_state
            ORDER BY message_id
            """
        ).fetchall()

        assert integrity == "ok", f"Integrity check failed: {integrity}"
        assert migrated_rows == original_rows, (
            "Records changed during migration"
        )

        # Test the new status inside a transaction, then roll it back.
        test_id = migrated_rows[0][0]
        connection.execute("BEGIN")
        connection.execute(
            "UPDATE message_state SET status = ? WHERE message_id = ?",
            ("prepared", test_id),
        )

        test_status = connection.execute(
            "SELECT status FROM message_state WHERE message_id = ?",
            (test_id,),
        ).fetchone()[0]

        assert test_status == "prepared"
        connection.rollback()

        final_count = connection.execute(
            "SELECT COUNT(*) FROM message_state"
        ).fetchone()[0]

        assert final_count == 16

        print("TEST COPY MIGRATION PASSED")
        print("Database:", DB_FILE.name)
        print("Integrity:", integrity)
        print("Records preserved:", final_count)
        print("Existing data unchanged:", migrated_rows == original_rows)
        print("Prepared status accepted: Yes")
        print("Test status change rolled back: Yes")
        print("Production database modified: No")
        print("WhatsApp message sent: No")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()