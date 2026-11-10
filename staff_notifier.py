
import os

from dotenv import load_dotenv
from whatsapp_sender import send_staff_alert_message

load_dotenv(override=True)


def notify_staff(customer_phone: str, reason: str) -> dict:
    """Send a staff alert only when staff alerts are enabled."""

    if os.getenv("STAFF_ALERTS_ENABLED", "false").strip().lower() != "true":
        raise RuntimeError(
            "Staff alerts are disabled by STAFF_ALERTS_ENABLED"
        )

    staff_number = os.getenv("STAFF_WHATSAPP_NUMBER", "").strip()

    if not staff_number:
        raise RuntimeError(
            "STAFF_WHATSAPP_NUMBER is missing from .env"
        )

    if not customer_phone or not reason:
        raise ValueError(
            "Customer phone and escalation reason are required"
        )

    alert = (
        "Nahar staff alert\n"
        "A WhatsApp conversation needs human assistance.\n"
        f"Reason: {reason}\n"
        f"Customer number: {customer_phone}\n"
        "Please review the conversation through an authorized channel."
    )

    return send_staff_alert_message(staff_number, alert)
