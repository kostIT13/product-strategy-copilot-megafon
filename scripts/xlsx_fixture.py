"""Synthetic XLSX fixture for import checks."""

from io import BytesIO
from openpyxl import Workbook


def make_xlsx(value=0.75):
    book = Workbook()
    book.properties.title = "Metrics research"
    sheet = book.active
    sheet.title = "Metrics"
    sheet.append(["Metric", "Value", "Formula"])
    sheet.append(["Retention", value, "=B2*100"])
    hidden = book.create_sheet("Internal")
    hidden["A1"] = "DO_NOT_IMPORT"
    hidden.sheet_state = "hidden"
    output = BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()
