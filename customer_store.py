
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font

FILE_PATH = Path(__file__).with_name("customers.xlsx")

HEADERS = [
    "Phone",
    "Customer Name",
    "Last Message",
    "Last Contact",
    "Status",
    "Notes",
    "Preferred Language",
]


def _open_customer_sheet():
    if not FILE_PATH.exists():
        raise FileNotFoundError(
            f"Customer workbook not found: {FILE_PATH}"
        )

    workbook = load_workbook(FILE_PATH)

    if "Customers" not in workbook.sheetnames:
        workbook.close()
        raise ValueError("Customers worksheet not found.")

    sheet = workbook["Customers"]

    old_headers = HEADERS[:6]
    existing_headers = [
        sheet.cell(1, col).value
        for col in range(1, 7)
    ]

    if all(value is None for value in existing_headers):
        for col, header in enumerate(HEADERS, start=1):
            sheet.cell(1, col, header)

    elif existing_headers == old_headers:
        language_header = sheet.cell(1, 7).value

        if language_header is None:
            sheet.cell(1, 7, "Preferred Language")
        elif language_header != "Preferred Language":
            workbook.close()
            raise ValueError(
                "Unexpected seventh customer column. "
                "No changes saved."
            )

    else:
        workbook.close()
        raise ValueError(
            "Existing customer columns do not match. "
            "No changes saved."
        )

    return workbook, sheet


def _find_customer_row(sheet, phone):
    for row in range(2, sheet.max_row + 1):
        if str(sheet.cell(row, 1).value or "") == phone:
            return row

    return None


def save_customer(
    phone: str,
    message: str,
    customer_name: str = "",
) -> None:
    if not phone or not message:
        raise ValueError("Phone and message are required.")

    workbook, sheet = _open_customer_sheet()

    try:
        row_number = _find_customer_row(sheet, phone)

        if row_number is None:
            row_number = sheet.max_row + 1
            sheet.cell(row_number, 1, phone)
            sheet.cell(row_number, 2, customer_name)
            sheet.cell(row_number, 5, "New")
            sheet.cell(row_number, 7, "pending")

        if customer_name:
            sheet.cell(row_number, 2, customer_name)

        sheet.cell(row_number, 3, message[:2000])
        sheet.cell(
            row_number,
            4,
            datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
        )

        for cell in sheet[1]:
            cell.font = Font(bold=True)

        workbook.save(FILE_PATH)

    finally:
        workbook.close()


def get_customer_language(phone: str) -> str:
    if not phone:
        return "pending"

    workbook, sheet = _open_customer_sheet()

    try:
        row_number = _find_customer_row(sheet, phone)

        if row_number is None:
            return "pending"

        language = str(
            sheet.cell(row_number, 7).value or "pending"
        ).strip().lower()

        if language not in ("en", "bn"):
            return "pending"

        return language

    finally:
        workbook.close()


def set_customer_language(phone: str, language: str) -> None:
    if not phone:
        raise ValueError("Phone is required.")

    language = str(language).strip().lower()

    if language not in ("en", "bn"):
        raise ValueError("Language must be 'en' or 'bn'.")

    workbook, sheet = _open_customer_sheet()

    try:
        row_number = _find_customer_row(sheet, phone)

        if row_number is None:
            row_number = sheet.max_row + 1
            sheet.cell(row_number, 1, phone)
            sheet.cell(row_number, 5, "New")

        sheet.cell(row_number, 7, language)

        for cell in sheet[1]:
            cell.font = Font(bold=True)

        workbook.save(FILE_PATH)

    finally:
        workbook.close()
