
import os
import logging
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

GRAPH_API_VERSION = "v23.0"
CUSTOMER_SERVICE_WINDOW_SECONDS = 24 * 60 * 60
MAX_RATE_LIMIT_RETRIES = 3

logger = logging.getLogger(__name__)


class WhatsAppSendError(RuntimeError):
    """A definite WhatsApp API rejection."""


class WhatsAppSendUncertain(RuntimeError):
    """The request outcome is unknown; never retry automatically."""


def _customer_window_is_open(
    customer_message_timestamp: int | str | None,
) -> bool:
    """Require a valid, recent incoming-message timestamp."""

    if isinstance(customer_message_timestamp, bool):
        return False

    if not isinstance(customer_message_timestamp, (int, str)):
        return False

    try:
        timestamp = int(customer_message_timestamp)
    except (TypeError, ValueError, OverflowError):
        return False

    if timestamp <= 0:
        return False

    age_seconds = time.time() - timestamp

    return 0 <= age_seconds < CUSTOMER_SERVICE_WINDOW_SECONDS


def _extract_meta_error(response: httpx.Response) -> dict[str, Any]:
    """Extract safe diagnostic information from a Meta API error."""

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not isinstance(data, dict):
        data = {}

    error = data.get("error", {})

    if not isinstance(error, dict):
        error = {}

    def safe_value(value: Any, limit: int = 300) -> str:
        if value is None:
            return "unknown"

        return " ".join(str(value).split())[:limit]

    return {
        "code": safe_value(error.get("code")),
        "subcode": safe_value(error.get("error_subcode")),
        "type": safe_value(error.get("type")),
        "message": safe_value(
            error.get("message", "No detailed error returned.")
        ),
        "user_title": safe_value(error.get("error_user_title")),
        "user_message": safe_value(error.get("error_user_msg")),
        "trace_id": safe_value(error.get("fbtrace_id")),
    }


def _send_text_message(
    recipient: str,
    message: str,
    enable_setting: str,
    customer_message_timestamp: int | str | None = None,
    require_open_window: bool = False,
    interactive_buttons: bool = False,
) -> dict:
    """Send a text message or interactive language-selection buttons."""

    enabled = (
        os.getenv(enable_setting, "false").strip().lower()
        == "true"
    )

    if not enabled:
        raise RuntimeError(
            f"WhatsApp sending is disabled by {enable_setting}"
        )

    if require_open_window and not _customer_window_is_open(
        customer_message_timestamp
    ):
        raise RuntimeError(
            "Customer-service window is closed or timestamp is missing; "
            "an approved WhatsApp template may be required."
        )

    token = os.getenv("WHATSAPP_TOKEN", "").strip()
    phone_number_id = os.getenv("PHONE_NUMBER_ID", "").strip()

    if not token or not phone_number_id:
        raise RuntimeError(
            "WhatsApp sender configuration is incomplete."
        )

    if not isinstance(recipient, str) or not recipient.strip():
        raise ValueError("Recipient is required.")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message text is required.")

    recipient = recipient.strip()
    message = message.strip()

    url = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/"
        f"{phone_number_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    if interactive_buttons:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message,
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "LANG_EN",
                                "title": "English",
                            },
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "LANG_BN",
                                "title": "বাংলা",
                            },
                        },
                    ],
                },
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message,
            },
        }

    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=20.0,
            )

        except httpx.TimeoutException as exc:
            logger.warning(
                "WhatsApp send timed out; outcome is uncertain. "
                "Automatic retry suppressed."
            )

            raise WhatsAppSendUncertain(
                "Send timed out. Check WhatsApp delivery status "
                "before attempting another send."
            ) from exc

        except httpx.RequestError as exc:
            logger.warning(
                "WhatsApp network error; outcome may be uncertain. "
                "Automatic retry suppressed."
            )

            raise WhatsAppSendUncertain(
                "Network error during send. Check delivery status "
                "before attempting another send."
            ) from exc

        if response.status_code == 429:

            if attempt < MAX_RATE_LIMIT_RETRIES:

                retry_after = response.headers.get(
                    "Retry-After", ""
                )

                try:
                    delay = float(retry_after)

                    if delay < 0:
                        raise ValueError("Negative retry delay")

                except (
                    TypeError,
                    ValueError,
                    OverflowError,
                ):
                    delay = float(2 ** attempt)

                delay = min(delay, 30.0)

                logger.warning(
                    "WhatsApp rate limited the request. "
                    "Retry %d of %d after %.1f seconds.",
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES,
                    delay,
                )

                time.sleep(delay)
                continue

            raise WhatsAppSendError(
                "WhatsApp API continued rate limiting the request "
                "after the retry limit."
            )

        if 500 <= response.status_code < 600:

            logger.warning(
                "WhatsApp API returned HTTP %s. "
                "Outcome is uncertain; automatic retry suppressed.",
                response.status_code,
            )

            raise WhatsAppSendUncertain(
                f"WhatsApp API server error HTTP "
                f"{response.status_code}. Verify delivery before retry."
            )

        if response.is_error:

            details = _extract_meta_error(response)

            logger.warning(
                "WhatsApp API rejection: HTTP=%s, "
                "Meta code=%s, subcode=%s, type=%s, message=%s, "
                "user_title=%s, user_message=%s, trace_id=%s",
                response.status_code,
                details["code"],
                details["subcode"],
                details["type"],
                details["message"],
                details["user_title"],
                details["user_message"],
                details["trace_id"],
            )

            raise WhatsAppSendError(
                f"HTTP {response.status_code}; "
                f"Meta code={details['code']}; "
                f"subcode={details['subcode']}; "
                f"type={details['type']}; "
                f"message={details['message']}; "
                f"user_title={details['user_title']}; "
                f"user_message={details['user_message']}; "
                f"trace_id={details['trace_id']}"
            )

        try:
            result = response.json()

        except ValueError as exc:
            raise WhatsAppSendUncertain(
                "Unexpected successful API response. "
                "Verify delivery before another attempt."
            ) from exc

        if not isinstance(result, dict):
            raise WhatsAppSendUncertain(
                "Unexpected API response format. "
                "Verify delivery before another attempt."
            )

        return result

    raise WhatsAppSendError(
        "WhatsApp send retry limit reached."
    )


def send_text_message(
    recipient: str,
    message: str,
    customer_message_timestamp: int | str | None = None,
) -> dict:
    """Send a customer reply only when enabled and inside 24 hours."""

    return _send_text_message(
        recipient,
        message,
        "AUTO_REPLY_ENABLED",
        customer_message_timestamp=customer_message_timestamp,
        require_open_window=True,
    )


def send_language_selection_message(
    recipient: str,
    customer_message_timestamp: int | str | None = None,
) -> dict:
    """Send English and Bengali language-selection buttons."""

    return _send_text_message(
        recipient,
        "Please choose your preferred language / "
        "আপনার পছন্দের ভাষা নির্বাচন করুন:",
        "AUTO_REPLY_ENABLED",
        customer_message_timestamp=customer_message_timestamp,
        require_open_window=True,
        interactive_buttons=True,
    )


def send_staff_alert_message(
    recipient: str,
    message: str,
) -> dict:
    """Send a staff alert only when independently enabled."""

    return _send_text_message(
        recipient,
        message,
        "STAFF_ALERTS_ENABLED",
    )
