"""Acquire public HTTP text using the shared pinned transport, without SQL."""

import hashlib
from urllib.parse import urlsplit
from product_strategy_agent.adapters.web.fetcher import PublicWebFetcher
from product_strategy_agent.adapters.web.extractor import StaticWebPageExtractor
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES


def read_web_source(url):
    page = PublicWebFetcher(max_bytes=MAX_TEXT_BYTES).fetch(url)
    document = StaticWebPageExtractor().extract(page)
    text = (document.text.strip() + "\n").encode("utf-8")
    if len(text) > MAX_TEXT_BYTES:
        raise ValueError("Extracted HTTP text exceeds the 10 MiB limit")
    return {
        "uri": page.final_url,
        "publisher": urlsplit(page.final_url).hostname,
        "extracted_title": document.title,
        "web": {
            "requested_url": page.requested_url,
            "final_url": page.final_url,
            "media_type": page.media_type,
            "charset": page.charset,
            "fetched_at": page.fetched_at,
            "response_sha256": hashlib.sha256(page.body).hexdigest(),
            "limitations": list(document.limitations),
        },
    }, text
