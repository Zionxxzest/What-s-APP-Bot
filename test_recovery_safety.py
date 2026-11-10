import sqlite3
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_file = Path(temp_dir) / "recovery_test.sqlite3"

        connection = sqlite3.connect(db_file)

        try:
            connection.execute("""
                CREATE TABLE message_state (
                    message_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    reply_text TEXT
                )
            """)

            message_id = "synthetic-recovery-test-001"
            reply_text = "Synthetic reply for recovery testing."

            connection.execute(
                """
                INSERT INTO message_state
                    (message_id, status, reply_text)
                VALUES (?, ?, ?)
                """,
                (message_id, "processing", reply_text),
            )
            connection.commit()

            row = connection.execute(
                """
                SELECT status, reply_text
                FROM message_state
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()

            assert row == ("processing", reply_text)

            duplicate = connection.execute(
                """
                SELECT COUNT(*)
                FROM message_state
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()[0]

            assert duplicate == 1

            print("TEST PASSED")
            print("Synthetic reply saved and read: Yes")
            print("Duplicate record created: No")
            print("Real WhatsApp message sent: No")
            print("Production database modified: No")

        finally:
            connection.close()


if __name__ == "__main__":
    main()