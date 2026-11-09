"""Offline validation of captured HTTP provenance; replay never resolves DNS."""

from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class WebCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    requested_url: Text
    final_url: Text
    media_type: Literal["text/html", "application/xhtml+xml", "text/plain"]
    charset: Text
    fetched_at: Text
    response_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    limitations: list[Text]

    @field_validator("requested_url", "final_url")
    @classmethod
    def http_url(cls, value):
        parts = urlsplit(value)
        if (
            any(ord(ch) < 33 or ord(ch) == 127 for ch in value)
            or parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
            or parts.port not in {None, 443 if parts.scheme == "https" else 80}
        ):
            raise ValueError("invalid captured HTTP URL")
        return value

    @field_validator("fetched_at")
    @classmethod
    def aware_time(cls, value):
        if datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError("capture timestamp requires a timezone")
        return value
