
import os
import tempfile
from pathlib import Path

import human_takeover
import message_state
import whatsapp_processor


def make_payload(sender, message_id, text):
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
                        "text": {"body": text},
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

    customer = "8801800000000"
    authorized_staff = "8801700000000"
    unauthorized_staff = "8801900000000"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # Use temporary databases and temporary authorization settings.
            message_state.DB_FILE = temp_path / "messages.sqlite3"
            human_takeover.DB_FILE = temp_path / "takeover.sqlite3"
            human_takeover.ENV_FILE = temp_path / ".env"
            human_takeover.ENV_FILE.write_text(
                f"AUTHORIZED_STAFF_PHONE={authorized_staff}\n",
                encoding="utf-8",
            )

            # Never write synthetic records to production Excel files.
            whatsapp_processor.save_customer = lambda **kwargs: None
            whatsapp_processor.log_message = lambda **kwargs: None
            whatsapp_processor.generate_reply = (
                lambda text: "Synthetic test reply"
            )

            os.environ["AUTO_REPLY_ENABLED"] = "false"
            os.environ["STAFF_ALERTS_ENABLED"] = "false"

            # 1. Ordinary messages still prepare a reply.
            ordinary = make_payload(
                customer,
                "processor-test-ordinary",
                "What are your business hours?",
            )
            results = whatsapp_processor.process_webhook_payload(ordinary)

            assert len(results) == 1
            assert results[0]["reply_text"] == "Synthetic test reply"
            assert message_state.get_message_status(
                "processor-test-ordinary"
            ) == "prepared"

            # 2. A human request activates persistent takeover.
            human = make_payload(
                customer,
                "processor-test-human",
                "I want to talk to a human",
            )
            results = whatsapp_processor.process_webhook_payload(human)

            assert len(results) == 1
            assert results[0]["escalate"] is True
            assert human_takeover.is_takeover_active(customer)

            # 3. Follow-up messages must not trigger the AI.
            before = "Synthetic test reply"
            suppressed = make_payload(
                customer,
                "processor-test-suppressed",
                "Here is some additional information",
            )
            results = whatsapp_processor.process_webhook_payload(suppressed)

            assert results == []
            assert human_takeover.is_takeover_active(customer)
            assert message_state.get_message_status(
                "processor-test-suppressed"
            ) == "failed"

            # 4. An unauthorized sender cannot resume the conversation.
            unauthorized = make_payload(
                unauthorized_staff,
                "processor-test-unauthorized-resume",
                f"/resume {customer}",
            )
            whatsapp_processor.process_webhook_payload(unauthorized)

            assert human_takeover.is_takeover_active(customer)

            # 5. Only the configured staff number can resume it.
            resume = make_payload(
                authorized_staff,
                "processor-test-authorized-resume",
                f"/resume {customer}",
            )
            whatsapp_processor.process_webhook_payload(resume)

            assert not human_takeover.is_takeover_active(customer)

            # 6. After resuming, a new ordinary message may be prepared.
            after_resume = make_payload(
                customer,
                "processor-test-after-resume",
                "Thank you",
            )
            results = whatsapp_processor.process_webhook_payload(
                after_resume
            )

            assert len(results) == 1
            assert results[0]["reply_text"] == "Synthetic test reply"
            assert message_state.get_message_status(
                "processor-test-after-resume"
            ) == "prepared"

            print("TEST PASSED")
            print("Temporary databases used: Yes")
            print("Ordinary reply preparation: Yes")
            print("Human request activates takeover: Yes")
            print("AI suppressed during takeover: Yes")
            print("Unauthorized resume blocked: Yes")
            print("Authorized resume accepted: Yes")
            print("AI reply preparation resumes afterward: Yes")
            print("Production database and Excel modified: No")
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
