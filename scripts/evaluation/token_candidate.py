"""Development-only lexical experiment; never registered in CLI or MCP."""

from collections import Counter, deque
import re

from product_strategy_agent.domain.projects.file_search import (
    MAX_QUOTE,
    search_snapshot,
    sections,
)

METHOD = "literal_then_token_window_v1"


def token_quote(text, wanted):
    """Find all distinct wanted tokens in one original-text 500-char window."""
    window, counts = deque(), Counter()
    for match in re.finditer(r"\w+", text):
        token = match.group().casefold()
        if token not in wanted:
            continue
        window.append((match.start(), token))
        counts[token] += 1
        while window and match.end() - window[0][0] > MAX_QUOTE:
            _, removed = window.popleft()
            counts[removed] -= 1
            if not counts[removed]:
                del counts[removed]
        if wanted <= counts.keys():
            start = window[0][0]
            return text[start : start + MAX_QUOTE]
    return None


def search_candidate(project_id, request, snapshot):
    # The unchanged kernel first validates ALL scopes/bounds, even after top-k.
    result = search_snapshot(project_id, request, snapshot)
    result["method"] = METHOD
    if result["hits"]:
        return result
    wanted = set(re.findall(r"\w+", request.query.casefold()))
    hits, matches = [], 0
    for source in sorted(snapshot.sources, key=lambda row: row.record["source_id"]):
        for locator, text in sections(source):
            quote = token_quote(text, wanted)
            if quote is None:
                continue
            matches += 1
            if len(hits) == request.limit:
                continue
            hits.append(
                {
                    **{
                        key: source.record[key]
                        for key in ("source_id", "title", "uri_or_path", "content_hash")
                    },
                    "locator": locator,
                    "quote": quote,
                }
            )
    return {
        **result,
        "hits": hits,
        "matched_sections": matches,
        "truncated": matches > len(hits),
    }
