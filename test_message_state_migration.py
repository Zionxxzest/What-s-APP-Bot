
import sqlite3
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "migration_test.sqlite3"
        connection = sqlite3.connect(db_path)

        try:
            # Reproduce the current schema in a temporary database.
            connection.execute("""
                CREATE TABLE message_state (
                    message_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (
                        status IN (
                            'processing', 'sent', 'failed', 'uncertain'
                        )
                    ),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reply_text TEXT,
                    last_error TEXT
                )
            """)

            connection.executemany(
                """
                INSERT INTO message_state
                    (message_id, status, reply_text)
                VALUES (?, ?, ?)
                """,
                [
                    ("synthetic-001", "processing", "Saved reply"),
                    ("synthetic-002", "sent", "Previously recorded reply"),
                    ("synthetic-003", "uncertain", "Outcome unknown"),
                ],
            )
            connection.commit()

            # Build the proposed schema with a distinct prepared state.
            connection.execute("""
                CREATE TABLE message_state_new (
                    message_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (
                        status IN (
                            'processing', 'prepared', 'sent',
                            'failed', 'uncertain'
                        )
                    ),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reply_text TEXT,
                    last_error TEXT
                )
            """)

            connection.execute("""
                INSERT INTO message_state_new
                    (message_id, status, updated_at, reply_text, last_error)
                SELECT message_id, status, updated_at, reply_text, last_error
                FROM message_state
            """)

            connection.execute("DROP TABLE message_state")
            connection.execute(
                "ALTER TABLE message_state_new RENAME TO message_state"
            )
            connection.commit()

            # Existing rows and their statuses must be preserved.
            rows = connection.execute("""
                SELECT message_id, status, reply_text
                FROM message_state
                ORDER BY message_id
            """).fetchall()

            assert rows == [
                ("synthetic-001", "processing", "Saved reply"),
                ("synthetic-002", "sent", "Previously recorded reply"),
                ("synthetic-003", "uncertain", "Outcome unknown"),
            ]

            # The new prepared status must be accepted.
            connection.execute(
                "UPDATE message_state SET status = 'prepared' "
                "WHERE message_id = ?",
                ("synthetic-001",),
            )
            connection.commit()

            status = connection.execute(
                "SELECT status FROM message_state WHERE message_id = ?",
                ("synthetic-001",),
            ).fetchone()[0]
            assert status == "prepared"

            # Invalid statuses must still be rejected.
            try:
                connection.execute(
                    "UPDATE message_state SET status = 'automatic_retry' "
                    "WHERE message_id = ?",
                    ("synthetic-003",),
                )
                connection.commit()
                raise AssertionError("Invalid status was accepted")
            except sqlite3.IntegrityError:
                connection.rollback()

            status = connection.execute(
                "SELECT status FROM message_state WHERE message_id = ?",
                ("synthetic-003",),
            ).fetchone()[0]
            assert status == "uncertain"

            print("TEST PASSED")
            print("Temporary database used: Yes")
            print("Prepared status supported: Yes")
            print("Existing statuses preserved: Yes")
            print("Invalid status rejected: Yes")
            print("Uncertain record preserved: Yes")
            print("Production database modified: No")
            print("WhatsApp message sent: No")

        finally:
            connection.close()


if __name__ == "__main__":
    main()
