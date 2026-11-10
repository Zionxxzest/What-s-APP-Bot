from openpyxl import load_workbook
from customer_store import save_customer, FILE_PATH

test_phone = "TEST_CUSTOMER_001"

save_customer(
    phone=test_phone,
    message="First test message",
    customer_name="Test Customer",
)

save_customer(
    phone=test_phone,
    message="Updated test message",
)

workbook = load_workbook(FILE_PATH, read_only=True)
try:
    sheet = workbook["Customers"]
    matches = [
        row
        for row in sheet.iter_rows(min_row=2, values_only=True)
        if str(row[0] or "") == test_phone
    ]

    assert len(matches) == 1, (
        f"Expected one test record, found {len(matches)}"
    )
    assert matches[0][2] == "Updated test message"
    assert matches[0][1] == "Test Customer"

    print("TEST PASSED")
    print("Customer record created and updated without duplication.")
finally:
    workbook.close()