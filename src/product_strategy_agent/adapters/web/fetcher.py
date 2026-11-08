"""Bounded explicit GET with redirect destination revalidation."""
from datetime import datetime, timezone
from email.message import Message
from http.client import HTTPException
import time
from urllib.parse import urljoin

from product_strategy_agent.adapters.web.http import request
from product_strategy_agent.adapters.web.policy import validate_target
from product_strategy_agent.domain.sources.web import FetchedPage, WebFetchError


class PublicWebFetcher:
    def __init__(self, *, max_bytes=10 * 1024 * 1024, max_redirects=3, timeout=10,
                 time_budget=30, validate=validate_target, transport=request):
        if min(max_bytes, timeout, time_budget) <= 0 or max_redirects < 0:
            raise ValueError("invalid web fetch limits")
        self.max_bytes, self.max_redirects = max_bytes, max_redirects
        self.timeout, self.time_budget = timeout, time_budget
        self.validate, self.transport = validate, transport

    def fetch(self, url: str) -> FetchedPage:
        deadline = time.monotonic() + self.time_budget
        requested_url = None
        seen = set()
        try:
            for hop in range(self.max_redirects + 1):
                target = self.validate(url)
                if requested_url is None:
                    requested_url = target.url
                if target.url in seen:
                    raise WebFetchError("redirect loop detected")
                seen.add(target.url)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WebFetchError("web fetch time budget exhausted")
                payload = self.transport(target, min(self.timeout, remaining), self.max_bytes, deadline)
                if payload.status in {301, 302, 303, 307, 308}:
                    if hop == self.max_redirects or not payload.headers.get("location"):
                        raise WebFetchError("redirect limit reached or Location is missing")
                    url = urljoin(target.url, payload.headers["location"])
                    if target.scheme == "https" and not url.lower().startswith("https://"):
                        raise WebFetchError("HTTPS redirects cannot downgrade to HTTP")
                    continue
                if payload.status != 200:
                    raise WebFetchError(f"HTTP request returned status {payload.status}")
                if len(payload.body) > self.max_bytes:
                    raise WebFetchError("HTTP response exceeds the byte limit")
                message = Message()
                message["content-type"] = payload.headers.get("content-type", "application/octet-stream")
                media_type = message.get_content_type()
                if media_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise WebFetchError("only HTML and plain-text HTTP responses are supported")
                return FetchedPage(requested_url, target.url, payload.body, media_type,
                    message.get_content_charset() or "utf-8-sig", datetime.now(timezone.utc).isoformat())
            raise WebFetchError("redirect limit exceeded")
        except WebFetchError:
            raise
        except (OSError, HTTPException, ValueError) as exc:
            raise WebFetchError("HTTP connection, TLS, or response parsing failed") from exc
