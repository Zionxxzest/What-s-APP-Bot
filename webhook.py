
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from message_state import set_message_status
from whatsapp_processor import (
    process_webhook_payload,
    send_prepared_reply,
)
from whatsapp_sender import (
    WhatsAppSendError,
    WhatsAppSendUncertain,
)
from message_log import log_message


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=True)

logging.basicConfig(level=logging.INFO)

app = FastAPI()


def auto_reply_enabled() -> bool:
    """Enable automatic replies only when explicitly configured."""
    return (
        os.getenv("AUTO_REPLY_ENABLED", "false").strip().lower()
        == "true"
    )


def matches_configured_phone_number(payload: dict) -> bool:
    """Validate the destination for message and status notifications."""

    configured_id = str(
        dotenv_values(ENV_FILE).get("PHONE_NUMBER_ID", "")
    ).strip()

    if (
        not configured_id
        or not isinstance(payload, dict)
        or payload.get("object") != "whatsapp_business_account"
    ):
        return False

    entries = payload.get("entry", [])

    if not isinstance(entries, list) or not entries:
        return False

    found_supported_event = False

    for entry in entries:
        if not isinstance(entry, dict):
            return False

        changes = entry.get("changes", [])

        if not isinstance(changes, list):
            return False

        for change in changes:
            if not isinstance(change, dict):
                return False

            if change.get("field") != "messages":
                continue

            value = change.get("value", {})

            if not isinstance(value, dict):
                return False

            messages = value.get("messages", [])
            statuses = value.get("statuses", [])

            if not isinstance(messages, list):
                return False

            if not isinstance(statuses, list):
                return False

            if not messages and not statuses:
                continue

            metadata = value.get("metadata", {})

            if not isinstance(metadata, dict):
                return False

            incoming_id = str(
                metadata.get("phone_number_id", "")
            ).strip()

            if incoming_id != configured_id:
                logging.warning(
                    "Phone ID mismatch: configured ends=%s, "
                    "incoming ends=%s",
                    configured_id[-4:],
                    incoming_id[-4:],
                )
                return False

            found_supported_event = True

    return found_supported_event


def verify_meta_signature(
    raw_body: bytes,
    signature: str | None,
) -> bool:
    """Validate Meta's X-Hub-Signature-256 header."""

    app_secret = os.getenv("META_APP_SECRET", "")

    if not app_secret or not signature:
        return False

    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def record_send_status(
    message_id: str,
    status: str,
    error: str | None = None,
) -> bool:
    """Record a send outcome without logging customer content."""

    saved = set_message_status(
        message_id,
        status,
        error=error,
    )

    if not saved:
        logging.critical(
            "Could not record outgoing message status=%s; "
            "message_id_present=%s",
            status,
            bool(message_id),
        )

    return saved


def log_successful_outgoing_reply(result: dict) -> bool:
    """
    Save an outgoing reply only after Meta accepts the send request.

    This records API acceptance, not final handset delivery.
    Failed and uncertain sends must never be logged as successful.
    """

    try:
        log_message(
            phone=result["sender"],
            text=result["reply_text"],
            customer_name=result.get("customer_name", ""),
            message_type="text",
            direction="outgoing",
        )

        logging.info(
            "Outgoing WhatsApp reply successfully logged to messages.xlsx."
        )

        return True

    except Exception:
        logging.exception(
            "WhatsApp API accepted the reply, but outgoing Excel logging "
            "failed. Do not resend the customer message automatically."
        )

        return False


@app.get("/")
async def home():
    """Health check without exposing credentials."""

    return {
        "status": "Webhook server is running",
        "auto_reply_enabled": auto_reply_enabled(),
    }


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Handle Meta webhook subscription verification."""

    verify_token = os.getenv("VERIFY_TOKEN", "")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if (
        mode == "subscribe"
        and verify_token
        and token == verify_token
        and challenge
    ):
        return PlainTextResponse(challenge)

    # Never log verification tokens or query strings.
    raise HTTPException(
        status_code=403,
        detail="Verification failed",
    )


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Verify and process incoming Meta webhook events."""

    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_meta_signature(raw_body, signature):
        logging.warning(
            "Webhook rejected: invalid or missing Meta signature."
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid signature",
        )

    try:
        body = json.loads(raw_body)

    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON",
        )

    if not matches_configured_phone_number(body):
        logging.warning(
            "Webhook rejected: missing or mismatched phone-number ID "
            "or unsupported event."
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook destination or event",
        )

    try:
        # Status-only notifications produce an empty results list.
        # Empty results are acknowledged without preparing replies.
        results = process_webhook_payload(body)

        logging.info(
            "Webhook processed; replies prepared: %d",
            len(results),
        )

        for result in results:
            logging.info(
                "Reply prepared; escalation required: %s; "
                "auto-reply enabled: %s",
                bool(result.get("escalate")),
                auto_reply_enabled(),
            )

        # Sending stays disabled unless .env explicitly enables it.
        if auto_reply_enabled():

            for result in results:

                message_id = result.get("message_id", "")

                # Never automatically answer messages escalated to staff.
                if result.get("escalate"):

                    record_send_status(
                        message_id,
                        "failed",
                        error=(
                            "Human escalation required; "
                            "automatic send suppressed"
                        ),
                    )

                    logging.info(
                        "Automated send suppressed because "
                        "human escalation is required."
                    )

                    continue

                try:
                    send_result = send_prepared_reply(result)

                except WhatsAppSendUncertain as exc:

                    record_send_status(
                        message_id,
                        "uncertain",
                        error=type(exc).__name__,
                    )

                    logging.error(
                        "Customer send outcome is uncertain. "
                        "Manual delivery verification is required; "
                        "do not automatically resend."
                    )

                except WhatsAppSendError as exc:

                    record_send_status(
                        message_id,
                        "failed",
                        error=type(exc).__name__,
                    )

                    logging.warning(
                        "WhatsApp rejected the customer reply."
                    )

                except (RuntimeError, ValueError) as exc:

                    record_send_status(
                        message_id,
                        "failed",
                        error=type(exc).__name__,
                    )

                    logging.warning(
                        "Customer reply blocked by sender safety "
                        "checks or configuration."
                    )

                except Exception as exc:

                    record_send_status(
                        message_id,
                        "uncertain",
                        error=type(exc).__name__,
                    )

                    logging.exception(
                        "Unexpected send outcome. "
                        "Do not automatically retry."
                    )

                else:
                    # A successful response means Meta accepted the send.
                    # Record sent status before attempting Excel logging.
                    status_saved = record_send_status(
                        message_id,
                        "sent",
                    )

                    if not status_saved:
                        logging.critical(
                            "WhatsApp API accepted a reply, but its "
                            "sent status could not be recorded. "
                            "Do not retry automatically."
                        )

                    # Log the outgoing message only after successful
                    # API acceptance. An Excel failure must not cause
                    # the successful WhatsApp message to be sent again.
                    logged = log_successful_outgoing_reply(result)

                    if logged:
                        logging.info(
                            "Outgoing reply accepted by WhatsApp API "
                            "and recorded in Excel."
                        )

                    # Do not print the response body or message content.
                    if not isinstance(send_result, dict):
                        logging.warning(
                            "Unexpected successful send response format."
                        )

    except HTTPException:
        raise

    except Exception:
        logging.exception("Webhook processing failed")

        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed",
        )

    return {"status": "EVENT_RECEIVED"}
