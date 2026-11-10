import tempfile
from pathlib import Path

import human_takeover


def main():
    original_db_file = human_takeover.DB_FILE
    original_env_file = human_takeover.ENV_FILE

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        try:
            # Use only a temporary database and temporary settings.
            human_takeover.DB_FILE = temp_path / "takeover_test.sqlite3"
            human_takeover.ENV_FILE = temp_path / ".env"
            human_takeover.ENV_FILE.write_text(
                "AUTHORIZED_STAFF_PHONE=8801700000000\n",
                encoding="utf-8",
            )

            customer = "8801800000000"
            authorized_staff = "8801700000000"
            unauthorized_staff = "8801900000000"

            # A new customer should not already be in takeover mode.
            assert not human_takeover.is_takeover_active(customer)

            # Activate takeover and confirm it persists in the database.
            assert human_takeover.activate_takeover(
                customer,
                reason="Synthetic test",
            )
            assert human_takeover.is_takeover_active(customer)

            # Unauthorized staff must not be allowed to resume.
            assert not human_takeover.resume_customer(
                customer,
                unauthorized_staff,
            )
            assert human_takeover.is_takeover_active(customer)

            # The configured staff number may resume this customer.
            assert human_takeover.resume_customer(
                customer,
                authorized_staff,
            )
            assert not human_takeover.is_takeover_active(customer)

            # A second resume should not claim success unnecessarily.
            assert not human_takeover.resume_customer(
                customer,
                authorized_staff,
            )

            print("TEST PASSED")
            print("Temporary database used: Yes")
            print("Takeover persisted: Yes")
            print("Unauthorized resume blocked: Yes")
            print("Authorized resume accepted: Yes")
            print("Second resume correctly rejected: Yes")
            print("Production database modified: No")
            print("WhatsApp message sent: No")

        finally:
            human_takeover.DB_FILE = original_db_file
            human_takeover.ENV_FILE = original_env_file


if __name__ == "__main__":
    main()