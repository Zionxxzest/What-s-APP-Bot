import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "message_state.sqlite3"


def main():
    connection = sqlite3.connect(
        DB_FILE.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        rows = connection.execute("""
            SELECT
                status,
                CASE
                    WHEN reply_text IS NOT NULL
                         AND TRIM(reply_text) <> ''
                    THEN 'reply_saved'
                    ELSE 'reply_missing'
                END AS reply_state,
                COUNT(*)
            FROM message_state
            GROUP BY status, reply_state
            ORDER BY status, reply_state
        """).fetchall()

        print("RECOVERY AUDIT (read-only)")
        print("Status | Reply state | Count")

        for status, reply_state, count in rows:
            print(f"{status} | {reply_state} | {count}")

        print("\nNo records modified.")
        print("No WhatsApp messages sent.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()