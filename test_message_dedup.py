
import uuid

from message_dedup import (
    is_message_new,
    mark_message_if_new,
    mark_message_completed,
)

message_id = f"dedup-test-{uuid.uuid4().hex}"

assert is_message_new(message_id), "New message should be accepted"
assert mark_message_if_new(message_id), "First recording should succeed"
assert not is_message_new(message_id), "Recorded message should not be new"
assert not mark_message_if_new(message_id), "Duplicate must not be recorded again"
assert not mark_message_completed(message_id), "Existing message should not be recorded twice"

print("TEST PASSED")
print("New messages accepted; duplicates rejected.")
