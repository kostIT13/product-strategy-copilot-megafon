"""Validate each HTTP destination and return pinned public addresses."""
from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit, quote

from product_strategy_agent.domain.sources.web import WebFetchError


@dataclass(frozen=True, slots=True)
class PublicTarget:
    url: str
    scheme: str
    host: str
    port: int
    path: str
    addresses: tuple[str, ...]


def public_address(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        return False
    if ip.version == 6:
        if ip.ipv4_mapped or ip.sixtofour or ip.teredo:
            return False
        if any(ip in ipaddress.ip_network(net) for net in ("64:ff9b::/96", "64:ff9b:1::/48", "2001::/23")):
            return False
    return not (ip.version == 4 and ip in ipaddress.ip_network("192.0.0.0/24"))


def validate_target(url: str, resolver=socket.getaddrinfo) -> PublicTarget:
    if not isinstance(url, str) or len(url) > 4096 or any(ord(ch) < 33 or ord(ch) == 127 for ch in url):
        raise WebFetchError("URL must be at most 4096 characters without whitespace or control characters")
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None or parts.password is not None:
            raise WebFetchError("only HTTP(S) URLs without credentials are supported")
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        if not host or "%" in host:
            raise WebFetchError("invalid or scoped destination hostname")
        port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
        if port != (443 if parts.scheme == "https" else 80):
            raise WebFetchError("only the standard HTTP/HTTPS ports are allowed")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            addresses = tuple(dict.fromkeys(info[4][0] for info in resolver(host, port, type=socket.SOCK_STREAM)))
        else:
            addresses = (str(literal),)
        if not addresses or not all(public_address(address) for address in addresses):
            raise WebFetchError("destination must resolve exclusively to public unicast addresses")
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        query = quote(parts.query, safe="=&?/:;,+%@$!()*'-._~")
        authority = f"[{host}]" if ":" in host else host
        normalized = urlunsplit((parts.scheme, authority, path, query, ""))
        return PublicTarget(normalized, parts.scheme, host, port, path + ("?" + query if query else ""), addresses)
    except WebFetchError:
        raise
    except (ValueError, UnicodeError, OSError) as exc:
        raise WebFetchError("destination URL or DNS resolution is invalid") from exc
