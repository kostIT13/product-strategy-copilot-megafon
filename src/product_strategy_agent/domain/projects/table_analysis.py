"""Bounded profiling and exact arithmetic over one captured table."""

from collections import Counter
import csv
from decimal import Decimal
from fractions import Fraction
from io import StringIO
import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_ROWS = 10000
MAX_COLUMNS = 256
MAX_CELLS = 100000
Label = Annotated[str, StringConstraints(min_length=1, max_length=256)]
SourceID = Annotated[str, StringConstraints(pattern=r"^S-[A-Za-z0-9_-]{1,120}$")]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Cell = tuple[str, str]
BLANK = ("blank", "")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?")
COORDINATE = re.compile(
    r"([A-Z]{1,3})([1-9][0-9]{0,4}) \[(number|text|datetime|boolean|formula|error)\] = (.+)"
)


class TableFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    column: Label
    equals: Annotated[str, StringConstraints(max_length=256)]


class TableAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    column: Label
    unit: Label
    period: Label
    filters: list[TableFilter] = Field(default_factory=list, max_length=8)


class TableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_id: SourceID
    expected_content_hash: Hash | None = None
    sheet: Label | None = None
    delimiter: Literal[",", ";", "\t"] = ","
    aggregate: TableAggregate | None = None


def _number(text):
    if len(text) <= 64 and NUMBER.fullmatch(text):
        value = Decimal(text)
        if abs(value.as_tuple().exponent) <= 64:
            return Fraction(value)
    return None


def _csv_cell(value: str) -> Cell:
    if not value.strip():
        return BLANK
    text = value.strip()
    if _number(text) is not None:
        return ("number", value)
    if text.casefold() in {"true", "false"}:
        return ("boolean", value)
    return ("text", value)


def _check_size(rows, width):
    if not 1 <= width <= MAX_COLUMNS or rows > MAX_ROWS or rows * width > MAX_CELLS:
        raise ValueError("Table exceeds supported row, column or cell limits")


def parse_csv(text, delimiter):
    reader = csv.reader(StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        header = next(reader, [])
        _check_size(1, len(header))
        rows = []
        for record in reader:
            _check_size(len(rows) + 2, len(header))
            if len(record) > len(header):
                raise ValueError("CSV record has more fields than the header")
            rows.append(
                tuple(map(_csv_cell, record)) + (BLANK,) * (len(header) - len(record))
            )
    except csv.Error:
        raise ValueError("CSV capture is malformed or has an oversized field") from None
    return header, rows


def _sheet_name(encoded):
    return re.sub(
        r"\\[\\rn]|''",
        lambda m: {
            r"\\": "\\",
            r"\r": "\r",
            r"\n": "\n",
            "''": "'",
        }[m[0]],
        encoded[1:-1],
    )


def parse_xlsx(text, sheet):
    if sheet is None:
        raise ValueError("Choose a visible XLSX sheet by name")
    prefix = None
    cells = {}
    width = height = 0
    found = False
    for line in StringIO(text):
        line = line.removesuffix("\n")
        if line.startswith("[sheet:'") and line.endswith("']"):
            name = line[len("[sheet:") : -1]
            prefix = name + "!" if _sheet_name(name) == sheet else None
            if prefix:
                if found:
                    raise ValueError("Duplicate worksheet in XLSX capture")
                found = True
            continue
        if prefix is None:
            continue
        match = (
            COORDINATE.fullmatch(line.removeprefix(prefix))
            if line.startswith(prefix)
            else None
        )
        if match is None:
            raise ValueError("Invalid cell in XLSX capture")
        letters, row, kind, value = match.groups()
        col = 0
        for letter in letters:
            col = 26 * col + ord(letter) - ord("A") + 1
        row = int(row)
        height, width = max(height, row), max(width, col)
        _check_size(height, width)
        key = (row, col)
        if key in cells:
            raise ValueError("Duplicate cell in XLSX capture")
        value = json.loads(value, parse_float=str, parse_int=str)
        if isinstance(value, bool):
            value = str(value).lower()
        if not isinstance(value, str):
            raise ValueError("Invalid value in XLSX capture")
        cells[key] = (kind, value) if value.strip() else BLANK
    if not cells:
        raise ValueError("Selected worksheet has no captured cells")
    header = [cells.get((1, col), BLANK)[1] for col in range(1, width + 1)]
    return header, [
        tuple(cells.get((row, col), BLANK) for col in range(1, width + 1))
        for row in range(2, height + 1)
    ]


def _ratio(value):
    if value is None:
        return None
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _aggregate(header, rows, request):
    try:
        column = header.index(request.column)
        filters = [(header.index(rule.column), rule.equals) for rule in request.filters]
    except ValueError:
        raise ValueError(
            "Aggregate or filter column is absent from the header"
        ) from None
    counts = Counter()
    values = []
    for row in rows:
        if any(row[index][1] != expected for index, expected in filters):
            continue
        counts["matched"] += 1
        kind, value = row[column]
        number = _number(value.strip()) if kind == "number" else None
        if number is not None:
            values.append(number)
        else:
            counts["missing" if kind == "blank" else "excluded"] += 1
    total = sum(values, Fraction()) if values else None
    return {
        "request": request.model_dump(mode="json"),
        "matched_rows": counts["matched"],
        "numeric_rows": len(values),
        "missing_rows": counts["missing"],
        "excluded_non_numeric_rows": counts["excluded"],
        "sum": _ratio(total),
        "mean": _ratio(total / len(values)) if values else None,
        "min": _ratio(min(values, default=None)),
        "max": _ratio(max(values, default=None)),
    }


def analyze_table(text, table_format, request):
    if table_format == "xlsx":
        if request.delimiter != ",":
            raise ValueError("Delimiter applies only to CSV")
        header, rows = parse_xlsx(text, request.sheet)
    else:
        if request.sheet is not None:
            raise ValueError("Sheet applies only to XLSX")
        header, rows = parse_csv(text, request.delimiter)
    header = [value.strip() for value in header]
    if any(not 1 <= len(value) <= 256 for value in header) or len(set(header)) != len(
        header
    ):
        raise ValueError(
            "Header names must be nonempty, distinct and at most 256 characters"
        )
    return {
        "format_version": 1,
        "table_format": table_format,
        "selection": request.model_dump(mode="json", exclude={"aggregate"}),
        "data_rows": len(rows),
        "duplicate_rows": len(rows) - len(set(rows)),
        "columns": [
            {
                "name": name,
                "missing": sum(row[index] == BLANK for row in rows),
                "types": dict(
                    Counter(row[index][0] for row in rows if row[index] != BLANK)
                ),
            }
            for index, name in enumerate(header)
        ],
        "aggregate": _aggregate(header, rows, request.aggregate)
        if request.aggregate
        else None,
    }
