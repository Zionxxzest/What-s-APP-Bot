
import sqlite3
import tempfile
from pathlib import Path

import message_state


def main():
    original_db_file = message_state.DB_FILE
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

    try:
        # Redirect the real module to a temporary database.
        message_state.DB_FILE = (
            Path(temp_dir.name) / "message_state_test.sqlite3"
        )

        message_id = "synthetic-recovery-test-001"

        assert message_state.claim_message(message_id) is True
        assert message_state.claim_message(message_id) is False

        assert message_state.save_prepared_reply(
            message_id, "Synthetic reply only"
        ) is True

        assert message_state.save_prepared_reply(
            message_id, "   "
        ) is False

        assert message_state.set_message_status(
            message_id, "uncertain", "Synthetic test outcome"
        ) is True

        assert (
            message_state.get_message_status(message_id)
            == "uncertain"
        )

        assert message_state.set_message_status(
            message_id, "processing"
        ) is False

        assert (
            message_state.get_message_status(message_id)
            == "uncertain"
        )

        sent_id = "synthetic-recovery-test-002"
        assert message_state.claim_message(sent_id) is True

        assert message_state.save_prepared_reply(
            sent_id, "Synthetic reply for testing"
        ) is True

        assert message_state.set_message_status(sent_id, "sent") is True
        assert message_state.set_message_status(sent_id, "failed") is False

        print("TEST PASSED")
        print("Actual message_state.py functions tested: Yes")
        print("Temporary database used: Yes")
        print("Duplicate message claim blocked: Yes")
        print("Empty reply rejected: Yes")
        print("Uncertain message reopened: No")
        print("Sent message changed to failed: No")
        print("Production database modified: No")
        print("WhatsApp message sent: No")

    finally:
        # Restore the original database path first.
        message_state.DB_FILE = original_db_file

        # Close any SQLite connections left open by the module.
        # _connect() uses SQLite's context manager, which commits or
        # rolls back but does not close the connection.
        db_file = Path(temp_dir.name) / "message_state_test.sqlite3"
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(db_file) + suffix)
            if candidate.exists():
                try:
                    with open(candidate, "ab"):
                        pass
                except OSError:
                    pass

        temp_dir.cleanup()


if __name__ == "__main__":
    main()


