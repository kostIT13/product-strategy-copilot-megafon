"""HTTP transport that connects only to a previously validated numeric IP."""
from dataclasses import dataclass
from http.client import HTTPConnection
import socket
import ssl
import time

from product_strategy_agent.adapters.web.policy import PublicTarget
from product_strategy_agent.domain.sources.web import WebFetchError


@dataclass(frozen=True, slots=True)
class HttpPayload:
    status: int
    headers: dict[str, str]
    body: bytes


class PinnedConnection(HTTPConnection):
    def __init__(self, target: PublicTarget, timeout: float):
        super().__init__(target.host, target.port, timeout=timeout)
        self.target = target

    def connect(self):
        # Numeric address avoids a second DNS lookup after policy validation.
        raw = socket.create_connection((self.target.addresses[0], self.port), self.timeout)
        try:
            if self.target.scheme == "https":
                context = ssl.create_default_context()
                context.set_alpn_protocols(["http/1.1"])
                self.sock = context.wrap_socket(raw, server_hostname=self.host)
            else:
                self.sock = raw
        except Exception:
            raw.close()
            raise


def request(target: PublicTarget, timeout: float, max_bytes: int, deadline: float) -> HttpPayload:
    connection = PinnedConnection(target, timeout)
    try:
        connection.request("GET", target.path, headers={
            "User-Agent": "product-strategy-agent/0.1", "Accept": "text/html,application/xhtml+xml,text/plain",
            "Accept-Encoding": "identity", "Connection": "close",
        })
        with connection.getresponse() as response:
            headers = {key.lower(): value for key, value in response.getheaders()}
            if response.status != 200:
                return HttpPayload(response.status, headers, b"")
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise WebFetchError("compressed HTTP responses are not supported")
            length = headers.get("content-length")
            if length is not None and (not length.isdigit() or int(length) > max_bytes):
                raise WebFetchError("HTTP Content-Length is invalid or exceeds the byte limit")
            chunks, count = [], 0
            while True:
                if time.monotonic() >= deadline:
                    raise WebFetchError("HTTP download exceeded its time budget")
                chunk = response.read(min(65536, max_bytes + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
                if count > max_bytes:
                    raise WebFetchError("HTTP response exceeds the byte limit")
            if length is not None and count != int(length):
                raise WebFetchError("HTTP body is shorter than its declared Content-Length")
            return HttpPayload(response.status, headers, b"".join(chunks))
    finally:
        connection.close()
