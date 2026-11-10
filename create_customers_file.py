from pathlib import Path
from openpyxl import Workbook, load_workbook

file_path = Path(__file__).with_name("customers.xlsx")

if file_path.exists():
    print(f"Existing customer file preserved: {file_path}")
else:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Customers"
    sheet.append([
        "Phone",
        "Customer Name",
        "Last Message",
        "Last Contact",
        "Status",
        "Notes",
    ])
    workbook.save(file_path)
    print(f"Created customer file: {file_path}")

workbook = load_workbook(file_path, read_only=True)
print("Worksheets:", ", ".join(workbook.sheetnames))
workbook.close()