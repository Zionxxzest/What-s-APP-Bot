
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "message_state.sqlite3"

ALLOWED_STATUSES = {
    "processing",
    "prepared",
    "sent",
    "failed",
    "uncertain",
}


def main():
    if not DB_FILE.is_file():
        raise FileNotFoundError("Production message-state database not found.")

    connection = sqlite3.connect(
        DB_FILE.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise AssertionError(
                f"SQLite integrity check failed: {integrity}"
            )

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(message_state)"
            ).fetchall()
        }

        required_columns = {
            "message_id",
            "status",
            "updated_at",
            "reply_text",
            "last_error",
        }

        if not required_columns.issubset(columns):
            raise AssertionError(
                "The message_state table is missing required columns."
            )

        rows = connection.execute("""
            SELECT
                status,
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN reply_text IS NOT NULL
                             AND TRIM(reply_text) <> ''
                        THEN 1 ELSE 0
                    END
                ) AS with_reply,
                SUM(
                    CASE
                        WHEN reply_text IS NULL
                             OR TRIM(reply_text) = ''
                        THEN 1 ELSE 0
                    END
                ) AS without_reply
            FROM message_state
            GROUP BY status
            ORDER BY status
        """).fetchall()

        totals = {
            status: (total, with_reply, without_reply)
            for status, total, with_reply, without_reply in rows
        }

        unknown_statuses = set(totals) - ALLOWED_STATUSES
        if unknown_statuses:
            raise AssertionError(
                f"Unexpected message statuses: {sorted(unknown_statuses)}"
            )

        total_records = sum(item[0] for item in totals.values())
        actual_total = connection.execute(
            "SELECT COUNT(*) FROM message_state"
        ).fetchone()[0]

        if total_records != actual_total:
            raise AssertionError(
                "Grouped counts do not match the database record count."
            )

        print("READ-ONLY PRODUCTION DATABASE CHECK")
        print("SQLite integrity:", integrity)
        print("Status | Total | With reply | Without reply")

        for status, total, with_reply, without_reply in rows:
            print(
                f"{status} | {total} | "
                f"{with_reply} | {without_reply}"
            )

        processing_missing = totals.get("processing", (0, 0, 0))[2]
        processing_saved = totals.get("processing", (0, 0, 0))[1]
        sent_missing = totals.get("sent", (0, 0, 0))[2]

        print("\nTotal records:", actual_total)
        print("Processing records without replies:", processing_missing)
        print("Processing records with saved replies:", processing_saved)
        print("Sent records without saved replies:", sent_missing)

        if processing_missing or processing_saved or sent_missing:
            print(
                "\nREVIEW NEEDED: Some records need investigation. "
                "No automatic recovery was performed."
            )
        else:
            print("\nNo listed status/reply inconsistencies found.")

        print("\nAUDIT PASSED")
        print("SQLite integrity verified: Yes")
        print("Counts checked against actual database: Yes")
        print("Database modified: No")
        print("WhatsApp message sent: No")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
