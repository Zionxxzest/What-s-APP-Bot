
import hashlib
import hmac
import json
import os
from unittest.mock import patch

from dotenv import dotenv_values
from fastapi.testclient import TestClient

from webhook import app

config = dotenv_values(".env")
app_secret = config.get("META_APP_SECRET", "")
phone_id = config.get("PHONE_NUMBER_ID", "")

assert app_secret, "META_APP_SECRET is not configured"
assert phone_id, "PHONE_NUMBER_ID is not configured"

client = TestClient(app)

def post_signed(payload):
    body = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

def payload(destination_id):
    value = {
        "messages": [{
            "id": "synthetic-destination-test",
            "from": "8801000000000",
            "type": "text",
            "text": {"body": "Synthetic test only"},
        }]
    }

    if destination_id is not None:
        value["metadata"] = {"phone_number_id": destination_id}

    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": value,
            }]
        }],
    }

with patch("webhook.process_webhook_payload", return_value=[]) as processor:
    matching = post_signed(payload(phone_id))
    wrong = post_signed(payload("wrong-test-id"))
    missing = post_signed(payload(None))

    print("Matching destination accepted:", matching.status_code == 200)
    print("Wrong destination rejected:", wrong.status_code == 400)
    print("Missing destination rejected:", missing.status_code == 400)
    print("Processor called for matching request:", processor.call_count == 1)
    print("Processor called exactly once for matching request:", processor.call_count == 1)

    assert matching.status_code == 200
    assert wrong.status_code == 400
    assert missing.status_code == 400
    assert processor.call_count == 1

print("ALL WEBHOOK DESTINATION TESTS PASSED")
print("Synthetic requests only; no WhatsApp messages sent.")
