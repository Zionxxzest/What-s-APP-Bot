
import os
import tempfile
import uuid
from pathlib import Path

import human_takeover
import message_state
import whatsapp_processor


def make_payload(message_id, message_text, sender):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "messages": [{
                        "from": sender,
                        "id": message_id,
                        "type": "text",
                        "text": {"body": message_text},
                    }]
                },
            }],
        }],
    }


def main():
    original_message_db = message_state.DB_FILE
    original_takeover_db = human_takeover.DB_FILE
    original_env_file = human_takeover.ENV_FILE
    original_save_customer = whatsapp_processor.save_customer
    original_log_message = whatsapp_processor.log_message
    original_generate_reply = whatsapp_processor.generate_reply
    old_auto = os.environ.get("AUTO_REPLY_ENABLED")
    old_staff = os.environ.get("STAFF_ALERTS_ENABLED")

    sender = "8801000000000"
    run_id = uuid.uuid4().hex

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # Isolate all message state and takeover state from production.
            message_state.DB_FILE = temp_path / "messages.sqlite3"
            human_takeover.DB_FILE = temp_path / "takeover.sqlite3"
            human_takeover.ENV_FILE = temp_path / ".env"
            human_takeover.ENV_FILE.write_text(
                "AUTHORIZED_STAFF_PHONE=8801700000000\n",
                encoding="utf-8",
            )

            # Do not write synthetic data into production Excel files.
            whatsapp_processor.save_customer = lambda **kwargs: None
            whatsapp_processor.log_message = lambda **kwargs: None
            whatsapp_processor.generate_reply = (
                lambda text: "Synthetic test reply"
            )

            os.environ["AUTO_REPLY_ENABLED"] = "false"
            os.environ["STAFF_ALERTS_ENABLED"] = "false"

            ordinary_id = f"escalation-ordinary-{run_id}"
            ordinary = whatsapp_processor.process_webhook_payload(
                make_payload(
                    ordinary_id,
                    "What are your business hours?",
                    sender,
                )
            )

            assert len(ordinary) == 1, "Expected ordinary message result"
            assert ordinary[0]["escalate"] is False
            assert ordinary[0]["reply_text"] == "Synthetic test reply"
            assert message_state.get_message_status(ordinary_id) == "prepared"

            human_id = f"escalation-human-{run_id}"
            human_request = whatsapp_processor.process_webhook_payload(
                make_payload(
                    human_id,
                    "I want to talk to a human",
                    sender,
                )
            )

            assert len(human_request) == 1, (
                "Expected human-request result"
            )
            assert human_request[0]["escalate"] is True
            assert human_request[0]["escalation_reason"]
            assert human_takeover.is_takeover_active(sender)

            print("TEST PASSED")
            print("Temporary databases used: Yes")
            print("Ordinary question: no escalation")
            print("Human request: escalation detected")
            print("Persistent takeover activated: Yes")
            print("Production database modified: No")
            print("Production Excel modified: No")
            print("WhatsApp message sent: No")

        finally:
            message_state.DB_FILE = original_message_db
            human_takeover.DB_FILE = original_takeover_db
            human_takeover.ENV_FILE = original_env_file
            whatsapp_processor.save_customer = original_save_customer
            whatsapp_processor.log_message = original_log_message
            whatsapp_processor.generate_reply = original_generate_reply

            if old_auto is None:
                os.environ.pop("AUTO_REPLY_ENABLED", None)
            else:
                os.environ["AUTO_REPLY_ENABLED"] = old_auto

            if old_staff is None:
                os.environ.pop("STAFF_ALERTS_ENABLED", None)
            else:
                os.environ["STAFF_ALERTS_ENABLED"] = old_staff


if __name__ == "__main__":
    main()
