"""URL policy, pinned transport, redirects, extraction and provenance checks."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import unittest

from product_strategy_agent.adapters.web.policy import validate_target
from product_strategy_agent.adapters.web.http import HttpPayload, PinnedConnection, request
from product_strategy_agent.adapters.web.fetcher import PublicWebFetcher
from product_strategy_agent.adapters.web.extractor import StaticWebPageExtractor
from product_strategy_agent.application.services.web_import_service import WebImportService
from product_strategy_agent.domain.sources.web import FetchedPage, WebFetchError


def public_dns(*args, **kwargs):
    return [(2, 1, 6, "", ("93.184.215.14", 443))]


def validate(url):
    return validate_target(url, public_dns)


def page(body=b"<title>Research</title><p>Source text.</p><script>hidden</script>", charset="utf-8"):
    return FetchedPage("https://example.org/start", "https://example.org/final", body,
                       "text/html", charset, datetime.now(timezone.utc).isoformat())


class WebPolicyTests(unittest.TestCase):
    def test_normalization_and_idna(self):
        target = validate("https://EXAMPLE.org:443/a?q=1#fragment")
        self.assertEqual(target.url, "https://example.org/a?q=1")
        self.assertEqual(target.addresses, ("93.184.215.14",))
        self.assertIn("xn--", validate("https://пример.рф/данные").host)
        self.assertIn("%", validate("https://пример.рф/данные").path)

    def test_non_public_and_transition_addresses_refused(self):
        for host in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "100.64.0.1", "224.0.0.1",
                     "192.0.0.8", "[::1]", "[::ffff:127.0.0.1]", "[64:ff9b::a00:1]", "[2002:a00:1::]"):
            with self.subTest(host=host), self.assertRaises(WebFetchError):
                validate("http://" + host + "/")

    def test_bad_url_and_ports_refused(self):
        for url in ("file:///etc/passwd", "ftp://example.org/a", "https://user:pass@example.org/",
                    "http://example.org:8080/", "http://example.org:0/", "https://example.org/\r\nx",
                    "http://[fe80::1%25eth0]/", "https://", "https://example.org/with space"):
            with self.subTest(url=url), self.assertRaises(WebFetchError):
                validate(url)

    def test_mixed_dns_addresses_refused(self):
        resolver = lambda *a, **k: public_dns() + [(2, 1, 6, "", ("10.0.0.1", 443))]
        with self.assertRaises(WebFetchError):
            validate_target("https://example.org/", resolver)


class WebFetcherTests(unittest.TestCase):
    def test_redirect_revalidated_and_original_url_preserved(self):
        transport = Mock(side_effect=[HttpPayload(302, {"location": "/final"}, b""),
            HttpPayload(200, {"content-type": "text/plain; charset=cp1251"}, "Привет".encode("cp1251"))])
        result = PublicWebFetcher(validate=validate, transport=transport).fetch("https://example.org/start")
        self.assertEqual(result.requested_url, "https://example.org/start")
        self.assertEqual(result.final_url, "https://example.org/final")
        self.assertEqual(result.charset, "cp1251")
        self.assertEqual(transport.call_count, 2)

    def test_redirect_to_private_or_downgrade_never_sent(self):
        for location in ("https://127.0.0.1/secret", "http://example.org/downgrade"):
            transport = Mock(return_value=HttpPayload(302, {"location": location}, b""))
            with self.subTest(location=location), self.assertRaises(WebFetchError):
                PublicWebFetcher(validate=validate, transport=transport).fetch("https://example.org/")
            self.assertEqual(transport.call_count, 1)

    def test_dns_is_rechecked_on_each_hop(self):
        resolver = Mock(side_effect=[public_dns(), [(2, 1, 6, "", ("127.0.0.1", 443))]])
        transport = Mock(return_value=HttpPayload(302, {"location": "/next"}, b""))
        fetcher = PublicWebFetcher(validate=lambda url: validate_target(url, resolver), transport=transport)
        with self.assertRaises(WebFetchError):
            fetcher.fetch("https://example.org/start")
        self.assertEqual(transport.call_count, 1)

    def test_loop_limit_and_missing_redirect_location(self):
        for payload, limit in ((HttpPayload(302, {"location": "/"}, b""), 3),
                               (HttpPayload(302, {"location": "/next"}, b""), 0),
                               (HttpPayload(302, {}, b""), 3)):
            with self.subTest(), self.assertRaises(WebFetchError):
                PublicWebFetcher(validate=validate, transport=Mock(return_value=payload), max_redirects=limit).fetch("https://example.org/")

    def test_http_errors_mime_and_body_limits(self):
        for payload in (HttpPayload(404, {}, b""), HttpPayload(200, {"content-type": "application/pdf"}, b"pdf"),
                        HttpPayload(200, {"content-type": "text/plain"}, b"x" * 9)):
            with self.subTest(), self.assertRaises(WebFetchError):
                PublicWebFetcher(validate=validate, transport=Mock(return_value=payload), max_bytes=8).fetch("https://example.org/")


class WebTransportTests(unittest.TestCase):
    def test_truncated_content_length_is_not_imported(self):
        with patch("product_strategy_agent.adapters.web.http.PinnedConnection") as cls:
            response = cls.return_value.getresponse.return_value.__enter__.return_value
            response.status = 200
            response.getheaders.return_value = [("Content-Length", "8")]
            response.read.side_effect = [b"short", b""]
            with self.assertRaises(WebFetchError):
                request(validate("https://example.org/"), 3, 8, float("inf"))

    def test_tls_uses_pinned_ip_but_original_hostname(self):
        target = validate("https://example.org/")
        with patch("product_strategy_agent.adapters.web.http.socket.create_connection") as connect, \
             patch("product_strategy_agent.adapters.web.http.ssl.create_default_context") as context:
            connection = PinnedConnection(target, 3)
            connection.connect()
            connect.assert_called_once_with(("93.184.215.14", 443), 3)
            context.return_value.wrap_socket.assert_called_once_with(connect.return_value, server_hostname="example.org")
            connection.close()

    def test_oversize_or_compressed_response_refused_and_closed(self):
        for headers in ([('Content-Length', '999')], [('Content-Encoding', 'gzip')], [('Content-Length', '-1')]):
            with self.subTest(headers=headers), patch("product_strategy_agent.adapters.web.http.PinnedConnection") as cls:
                response = cls.return_value.getresponse.return_value.__enter__.return_value
                response.status = 200
                response.getheaders.return_value = headers
                with self.assertRaises(WebFetchError):
                    request(validate("https://example.org/"), 3, 8, float("inf"))
                cls.return_value.close.assert_called_once()

    def test_streaming_limit_without_content_length(self):
        with patch("product_strategy_agent.adapters.web.http.PinnedConnection") as cls:
            response = cls.return_value.getresponse.return_value.__enter__.return_value
            response.status, response.getheaders.return_value = 200, []
            response.read.return_value = b"x" * 9
            with self.assertRaises(WebFetchError):
                request(validate("https://example.org/"), 3, 8, float("inf"))


class WebExtractionTests(unittest.TestCase):
    def test_source_title_limits_checked_before_persistence(self):
        from product_strategy_agent.application.services.source_service import SourceService
        store = Mock()
        for title in ("x" * 501, "invalid\x00title"):
            with self.subTest(), self.assertRaises(ValueError):
                SourceService(store).register("demo", "https://example.org/", "web_page", "text", title=title)
        store.register_revision.assert_not_called()

    def test_html_and_provenance_reach_source_service(self):
        fetched = page()
        sources = Mock()
        service = WebImportService(Mock(fetch=Mock(return_value=fetched)), StaticWebPageExtractor(), sources)
        service.import_url("demo", fetched.requested_url)
        args, kwargs = sources.register.call_args
        self.assertEqual(args, ("demo", fetched.requested_url, "web_page", "Source text."))
        self.assertEqual(kwargs["title"], "Research")
        self.assertEqual(kwargs["provenance"]["final_url"], fetched.final_url)
        self.assertEqual(len(kwargs["provenance"]["response_sha256"]), 64)

    def test_decoding_and_empty_text_fail(self):
        for fetched in (page(b"\xff", "utf-8"), page(b"hello", "invalid-codec"), page(b"<script>only script</script>")):
            with self.subTest(), self.assertRaises(WebFetchError):
                StaticWebPageExtractor().extract(fetched)
