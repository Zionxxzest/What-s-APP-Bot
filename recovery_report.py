
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
                COUNT(*),
                SUM(
                    CASE WHEN reply_text IS NOT NULL
                    AND TRIM(reply_text) <> ''
                    THEN 1 ELSE 0 END
                ),
                SUM(
                    CASE WHEN reply_text IS NULL
                    OR TRIM(reply_text) = ''
                    THEN 1 ELSE 0 END
                )
            FROM message_state
            GROUP BY status
            ORDER BY status
        """).fetchall()

        print("SAFE RECOVERY REPORT (read-only)")
        print("Status | Total | With saved reply | Without saved reply")
        for status, total, saved, missing in rows:
            print(f"{status} | {total} | {saved} | {missing}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
   