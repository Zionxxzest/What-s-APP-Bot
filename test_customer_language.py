
from customer_store import (
    get_customer_language,
    set_customer_language,
    save_customer,
)

phone = "TEST_LANGUAGE_001"

save_customer(
    phone=phone,
    message="Language preference test",
    customer_name="Language Test",
)

assert get_customer_language(phone) == "pending"

set_customer_language(phone, "bn")
assert get_customer_language(phone) == "bn"

set_customer_language(phone, "en")
assert get_customer_language(phone) == "en"

print("TEST PASSED")
print("Default language: pending")
print("Bengali preference: saved")
print("English preference: saved")
