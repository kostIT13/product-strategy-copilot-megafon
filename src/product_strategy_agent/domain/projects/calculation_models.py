"""Explicit two-operand arithmetic contracts; context labels are authored assertions."""

from typing import Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from product_strategy_agent.domain.projects.baseline_numbers import NumberAnchor

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
DecimalText = Annotated[
    str,
    StringConstraints(pattern=r"^[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$", max_length=80),
]
OPERANDS = {
    "percentage": {"numerator", "denominator"},
    "ratio": {"numerator", "denominator"},
    "percentage_points": {"baseline", "current"},
    "relative_change_percent": {"baseline", "current"},
}
UNITS = {
    "percentage": "%",
    "ratio": "ratio",
    "percentage_points": "percentage_points",
    "relative_change_percent": "%",
}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Context(Model):
    metric: Text
    population: Text
    period: Text
    conditions: Text


class Operand(Model):
    anchor: NumberAnchor
    context: Context


class Rounding(Model):
    decimal_places: int = Field(ge=0, le=12)
    mode: Literal["half_even"]


class Calculation(Model):
    calculation_id: Annotated[str, StringConstraints(pattern=r"^CALC-[0-9]{1,6}$")]
    operation: Literal[
        "percentage", "ratio", "percentage_points", "relative_change_percent"
    ]
    period_relation: Literal["same", "distinct"]
    operands: dict[str, Operand]
    expected_value: DecimalText
    result_unit: Literal["%", "ratio", "percentage_points"]
    rounding: Rounding | None = None

    @model_validator(mode="after")
    def operand_names(self):
        if set(self.operands) != OPERANDS[self.operation]:
            raise ValueError("operation requires exactly its named pair of operands")
        return self


class Calculations(Model):
    schema_version: Literal[1]
    calculations: list[Calculation] = Field(min_length=1, max_length=10)

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("calculation schema_version must be integer 1")
        return value

    @model_validator(mode="after")
    def distinct_ids(self):
        ids = [row.calculation_id for row in self.calculations]
        if len(ids) != len(set(ids)):
            raise ValueError("calculation IDs must be distinct")
        return self
