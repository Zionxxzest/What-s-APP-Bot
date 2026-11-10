
from message_handler import extract_incoming_messages

sample_event = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messages": [
                            {
                                "id": "test-message-001",
                                "from": "8801700000000",
                                "timestamp": "1790000000",
                                "type": "text",
                                "text": {
                                    "body": "Hello, webhook test"
                                }
                            },
                            {
                                "id": "test-message-002",
                                "from": "8801700000000",
                                "type": "text",
                                "text": {
                                    "body": "Message without timestamp"
                                }
                            },
                            {
                                "id": "test-message-003",
                                "from": "8801700000000",
                                "timestamp": "1790000002",
                                "type": "interactive",
                                "interactive": {
                                    "type": "button_reply",
                                    "button_reply": {
                                        "id": "LANG_EN",
                                        "title": "English"
                                    }
                                }
                            },
                            {
                                "id": "test-message-004",
                                "from": "8801700000000",
                                "timestamp": "1790000003",
                                "type": "interactive",
                                "interactive": {
                                    "type": "button_reply",
                                    "button_reply": {
                                        "id": "LANG_BN",
                                        "title": "বাংলা"
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

result = extract_incoming_messages(sample_event)

assert len(result) == 4

assert result[0]["text"] == "Hello, webhook test"
assert result[0]["timestamp"] == 1790000000
assert result[0]["message_type"] == "text"

assert result[1]["timestamp"] is None

assert result[2]["button_id"] == "LANG_EN"
assert result[2]["text"] == "English"

assert result[3]["button_id"] == "LANG_BN"
assert result[3]["text"] == "বাংলা"

print("TEST PASSED")
print("Normal text messages: Yes")
print("English button recognized: Yes")
print("Bengali button recognized: Yes")
print("Missing timestamp handled safely: Yes")
