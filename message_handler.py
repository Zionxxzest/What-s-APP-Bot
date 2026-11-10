
def extract_incoming_messages(payload):
    """Extract WhatsApp text messages and interactive button replies."""
    messages = []

    if not isinstance(payload, dict):
        return messages

    if payload.get("object") != "whatsapp_business_account":
        return messages

    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue

        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue

            if change.get("field") != "messages":
                continue

            value = change.get("value", {})
            if not isinstance(value, dict):
                continue

            contact_names = {}
            contacts = value.get("contacts", [])

            if isinstance(contacts, list):
                for contact in contacts:
                    if not isinstance(contact, dict):
                        continue

                    wa_id = contact.get("wa_id", "")
                    profile = contact.get("profile", {})

                    if not isinstance(profile, dict):
                        profile = {}

                    name = profile.get("name", "")

                    if (
                        isinstance(wa_id, str)
                        and wa_id.strip()
                        and isinstance(name, str)
                        and name.strip()
                    ):
                        contact_names[wa_id.strip()] = name.strip()

            incoming = value.get("messages", [])

            if not isinstance(incoming, list):
                continue

            for message in incoming:
                if not isinstance(message, dict):
                    continue

                message_type = message.get("type", "")
                text_body = ""
                button_id = ""

                if message_type == "text":
                    text_data = message.get("text", {})

                    if not isinstance(text_data, dict):
                        continue

                    text_body = text_data.get("body", "")

                elif message_type == "interactive":
                    interactive = message.get("interactive", {})

                    if not isinstance(interactive, dict):
                        continue

                    button_reply = interactive.get(
                        "button_reply", {}
                    )

                    if not isinstance(button_reply, dict):
                        continue

                    button_id = button_reply.get("id", "")
                    button_title = button_reply.get("title", "")

                    if not isinstance(button_id, str):
                        continue

                    if not isinstance(button_title, str):
                        button_title = ""

                    text_body = button_title or button_id

                else:
                    continue

                sender = message.get("from", "")
                message_id = message.get("id", "")

                if not all(
                    isinstance(item, str) and item.strip()
                    for item in (sender, text_body, message_id)
                ):
                    continue

                raw_timestamp = message.get("timestamp")
                timestamp = None

                if isinstance(raw_timestamp, (str, int)) and not isinstance(
                    raw_timestamp, bool
                ):
                    try:
                        timestamp = int(raw_timestamp)

                        if timestamp < 0:
                            timestamp = None

                    except (TypeError, ValueError, OverflowError):
                        timestamp = None

                sender = sender.strip()

                messages.append({
                    "sender": sender,
                    "customer_name": contact_names.get(sender, ""),
                    "text": text_body.strip(),
                    "message_id": message_id.strip(),
                    "timestamp": timestamp,
                    "message_type": message_type,
                    "button_id": button_id,
                })

    return messages
