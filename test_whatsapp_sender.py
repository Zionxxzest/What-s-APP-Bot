
import os

from whatsapp_sender import send_text_message


def main():
    # Explicitly disable sending for this test.
    os.environ["AUTO_REPLY_ENABLED"] = "false"

    try:
        send_text_message(
            "8801000000000",
            "Synthetic safety test; do not send."
        )
    except RuntimeError as exc:
        if "AUTO_REPLY_ENABLED" in str(exc):
            print("TEST PASSED")
            print("Sending disabled: True")
            print("Real WhatsApp message sent: No")
            return

        raise

    raise AssertionError(
        "Safety test failed: sender did not block the request."
    )


if __name__ == "__main__":
    main()
