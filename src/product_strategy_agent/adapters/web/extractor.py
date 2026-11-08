"""Convert fetched HTML/plain text through the existing extraction contract."""
from product_strategy_agent.adapters.documents.html import HtmlTextExtractor
from product_strategy_agent.domain.sources.documents import ExtractedDocument
from product_strategy_agent.domain.sources.web import FetchedPage, WebFetchError


class StaticWebPageExtractor:
    def extract(self, page: FetchedPage) -> ExtractedDocument:
        try:
            text = page.body.decode(page.charset)
        except (UnicodeError, LookupError) as exc:
            raise WebFetchError("HTTP body could not be decoded using its declared charset") from exc
        title = page.final_url
        if page.media_type != "text/plain":
            parser = HtmlTextExtractor()
            parser.feed(text)
            parser.close()
            text, extracted_title = parser.result()
            title = extracted_title or title
        if not text.strip() or "\x00" in text:
            raise WebFetchError("HTTP response contains no usable text")
        return ExtractedDocument(page.requested_url, text, title, "web_page", (
            "Static HTTP text only; no JavaScript execution, linked-resource loading, authentication or crawling.",))
