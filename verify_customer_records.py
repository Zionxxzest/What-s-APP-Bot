from openpyxl import load_workbook
from customer_store import FILE_PATH

workbook = load_workbook(FILE_PATH, read_only=True)

try:
    sheet = workbook["Customers"]

    print("Customer records found:")
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[0] and str(row[0]).startswith("880"):
            print(f"Phone: {row[0]} | Name: {row[1]} | Last message: {row[2]}")

    print("\nExcel workbook verification completed.")
finally:
    workbook.close()