from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font


FILE_PATH = Path(__file__).with_name("messages.xlsx")

HEADERS = [
    "Date",
    "Time",
    "Customer Name",
    "Phone",
    "Text",
    "Type",
    "Direction",
]


def log_message(
    phone: str,
    text: str,
    customer_name: str = "",
    message_type: str = "text",
    direction: str = "incoming",
) -> None:
    """Append one message to messages.xlsx using Bangladesh time."""

    if not phone.strip() or not text.strip():
        raise ValueError("Phone and message text are required.")

    now = datetime.now(ZoneInfo("Asia/Dhaka"))

    if FILE_PATH.exists():
        workbook = load_workbook(FILE_PATH)
        if "Messages" not in workbook.sheetnames:
            workbook.close()
            raise ValueError(
                "Messages worksheet is missing from messages.xlsx."
            )
        sheet = workbook["Messages"]
    else:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Messages"
        for column, header in enumerate(HEADERS, start=1):
            sheet.cell(row=1, column=column, value=header)

    try:
        existing_headers = [
            sheet.cell(row=1, column=column).value
            for column in range(1, len(HEADERS) + 1)
        ]

        if existing_headers != HEADERS:
            raise ValueError(
                "Message log headers are incorrect. "
                "No message was saved."
            )

        sheet.append([
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            customer_name.strip(),
            phone.strip(),
            text.strip()[:4000],
            message_type,
            direction,
        ])

        for cell in sheet[1]:
            cell.font = Font(bold=True)

        workbook.save(FILE_PATH)
    finally:
        workbook.close()