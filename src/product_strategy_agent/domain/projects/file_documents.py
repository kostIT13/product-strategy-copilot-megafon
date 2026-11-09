"""Captured document provenance and exact page/cell citation scopes."""

import json
import re
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DOCUMENT_SUFFIXES = frozenset({".pdf", ".docx", ".xlsx"})


class DocumentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    format: Literal["pdf", "docx", "xlsx"]
    locator: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    limitations: list[
        Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    ] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def native_locator(self):
        if self.format == "pdf":
            match = re.fullmatch(r"pages:1-([1-9]\d{0,2})", self.locator)
            valid = match is not None and int(match[1]) <= 200
        else:
            valid = (
                self.locator == "workbook:visible-sheets"
                if self.format == "xlsx"
                else bool(re.fullmatch(r"paragraphs:1-[1-9]\d*", self.locator))
            )
        if not valid:
            raise ValueError("document locator does not match its captured format")
        return self


def document_excerpt(source, text, locator):
    """Return exact native scope, None for existing plain-text locator syntax."""
    locator = locator.strip()
    if locator.lower().startswith("page:"):
        if source.get("document_format") != "pdf":
            raise ValueError("page locator requires a captured PDF source")
        match = re.fullmatch(r"page:([1-9]\d*)", locator, re.IGNORECASE)
        extent = re.fullmatch(r"pages:1-([1-9]\d*)", source.get("locator", ""))
        if not match or not extent:
            raise ValueError("invalid PDF page locator or extent")
        count, page = int(extent[1]), int(match[1])
        if count > 200:
            raise ValueError("PDF page extent exceeds the supported limit")
        markers = list(re.finditer(r"^\[page:(\d+)\][ \t]*\r?$", text, re.MULTILINE))
        if [int(row[1]) for row in markers] != list(range(1, count + 1)):
            raise ValueError("ambiguous or corrupt PDF page markers")
        if page > count:
            raise ValueError("page locator is outside the captured PDF")
        return text[
            markers[page - 1].end() : markers[page].start()
            if page < count
            else len(text)
        ].strip()
    if locator.lower().startswith("cell:"):
        if source.get("document_format") != "xlsx":
            raise ValueError("cell locator requires a captured XLSX source")
        target = locator[5:]
        if not re.fullmatch(r"'(?:[^'\r\n]|'')+'![A-Z]{1,3}[1-9]\d{0,6}", target):
            raise ValueError(
                "use the exact quoted sheet/cell reference from extracted text"
            )
        matches = [
            re.fullmatch(re.escape(target) + r" \[[a-z]+\] = (.*)", line)
            for line in text.splitlines()
        ]
        matches = [match for match in matches if match]
        if len(matches) != 1:
            raise ValueError("cell is absent or ambiguous in visible extracted sheets")
        value = json.loads(matches[0][1])
        return (
            value
            if isinstance(value, str)
            else json.dumps(value, ensure_ascii=False, allow_nan=False)
        )
    return None
