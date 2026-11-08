"""Bounded XLSX cell extraction without evaluating formulas or external links."""

from datetime import date, datetime, time
from io import BytesIO
import json
import re
from zipfile import BadZipFile, ZipFile

from product_strategy_agent.domain.sources.documents import DocumentExtractionError


class XlsxTextExtractor:
    def __init__(self, max_sheets=20, max_rows=10000, max_columns=256, max_cells=100000,
                 max_uncompressed_bytes=64 * 1024 * 1024, max_text_bytes=10 * 1024 * 1024):
        if min(max_sheets, max_rows, max_columns, max_cells, max_uncompressed_bytes, max_text_bytes) < 1:
            raise ValueError("XLSX limits must be positive")
        self.max_sheets, self.max_rows, self.max_columns = max_sheets, max_rows, max_columns
        self.max_cells = max_cells
        self.max_uncompressed_bytes, self.max_text_bytes = max_uncompressed_bytes, max_text_bytes

    def extract(self, data: bytes) -> tuple[str, str, int, int, int]:
        try:
            from openpyxl import load_workbook
            from openpyxl.utils.cell import column_index_from_string
            from defusedxml import ElementTree
            from defusedxml.common import DefusedXmlException
            from lxml.etree import XMLSyntaxError
            from xml.etree.ElementTree import ParseError
        except ImportError as exc:
            raise DocumentExtractionError('XLSX support requires: pip install -e ".[documents]"') from exc

        workbook = None
        try:
            with ZipFile(BytesIO(data)) as archive:
                parts = archive.infolist()
                names = {part.filename for part in parts}
                if len(parts) > 2048 or sum(part.file_size for part in parts) > self.max_uncompressed_bytes:
                    raise DocumentExtractionError("XLSX expanded-size or part-count limit exceeded")
                if any(part.flag_bits & 1 for part in parts):
                    raise DocumentExtractionError("encrypted XLSX is not supported")
                if not {"[Content_Types].xml", "xl/workbook.xml"} <= names:
                    raise DocumentExtractionError("XLSX package is missing required workbook parts")
                if any(name.lower().endswith("vbaproject.bin") for name in names):
                    raise DocumentExtractionError("macro-enabled packages are not supported")
                sheets = [name for name in names if name.startswith("xl/worksheets/") and name.endswith(".xml")]
                if not 1 <= len(sheets) <= self.max_sheets:
                    raise DocumentExtractionError("XLSX sheet-count limit exceeded or no worksheets")
                cells = 0
                # Inspect actual coordinates, not unreliable worksheet dimensions,
                # before read-only iteration can expand sparse rows or columns.
                for name in sheets:
                    for _, element in ElementTree.iterparse(BytesIO(archive.read(name)), events=("end",)):
                        tag = element.tag.rsplit("}", 1)[-1]
                        if tag == "row" and not 1 <= int(element.attrib.get("r", "0")) <= self.max_rows:
                            raise DocumentExtractionError("XLSX row limit exceeded")
                        if tag == "c":
                            match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", element.attrib.get("r", ""))
                            if not match or int(match[2]) > self.max_rows or column_index_from_string(match[1]) > self.max_columns:
                                raise DocumentExtractionError("XLSX cell coordinate exceeds supported limits")
                            cells += 1
                            if cells > self.max_cells:
                                raise DocumentExtractionError("XLSX cell-count limit exceeded")
                        element.clear()

            workbook = load_workbook(BytesIO(data), read_only=True, data_only=False, keep_links=False)
            if len(workbook.worksheets) > self.max_sheets:
                raise DocumentExtractionError("XLSX sheet-count limit exceeded")
            lines: list[str] = []
            total_bytes = visible = hidden = formulas = nonempty = 0

            def append(line):
                nonlocal total_bytes
                total_bytes += len((line + "\n").encode("utf-8"))
                if total_bytes > self.max_text_bytes:
                    raise DocumentExtractionError("XLSX text-output limit exceeded")
                lines.append(line)

            for sheet in workbook.worksheets:
                if sheet._worksheet_path not in sheets:
                    raise DocumentExtractionError("XLSX worksheet points to an unchecked package part")
                if sheet.sheet_state != "visible":
                    hidden += 1
                    continue
                visible += 1
                sheet_name = "'" + sheet.title.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace("'", "''") + "'"
                append(f"[sheet:{sheet_name}]")
                sheet.reset_dimensions()
                for row in sheet.iter_rows():
                    for cell in row:
                        value = cell.value
                        if value is None:
                            continue
                        nonempty += 1
                        if cell.data_type == "f":
                            if not isinstance(value, str):
                                raise DocumentExtractionError("XLSX array/data-table formulas are not supported")
                            kind = "formula"
                            formulas += 1
                        elif isinstance(value, (datetime, date, time)):
                            kind, value = "datetime", value.isoformat()
                        elif isinstance(value, bool):
                            kind = "boolean"
                        elif isinstance(value, (int, float)):
                            kind = "number"
                        else:
                            kind = "error" if cell.data_type == "e" else "text"
                            value = str(value)
                        append(f"{sheet_name}!{cell.coordinate} [{kind}] = {json.dumps(value, ensure_ascii=False, allow_nan=False)}")
            if not nonempty:
                raise DocumentExtractionError("XLSX has no non-empty visible cells")
            return "\n".join(lines), workbook.properties.title or "", visible, hidden, formulas
        except (BadZipFile, KeyError, ValueError, TypeError, OSError, ParseError, XMLSyntaxError, DefusedXmlException) as exc:
            if isinstance(exc, DocumentExtractionError):
                raise
            raise DocumentExtractionError("XLSX workbook could not be parsed") from exc
        finally:
            if workbook is not None:
                workbook.close()
