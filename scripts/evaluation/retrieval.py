"""Measure the shipped literal search kernel on a fixed synthetic gold corpus."""

import hashlib
import json
from pathlib import Path
from time import perf_counter

from product_strategy_agent.domain.projects.file_search import (
    FileSearchRequest,
    SearchSnapshot,
    SearchSource,
    search_snapshot,
)

FIXTURE = Path(__file__).resolve().parents[2] / "evals/retrieval/corpus.json"


def score(retrieved, relevant):
    """Set precision/recall; empty denominators stay unknown, not perfect."""
    found, gold = set(retrieved), set(relevant)
    correct = len(found & gold)
    return {
        "precision": correct / len(found) if found else None,
        "recall": correct / len(gold) if gold else None,
        "true_positive": correct,
        "false_positive": len(found - gold),
        "false_negative": len(gold - found),
    }


def evaluate(data, retrieve=search_snapshot, *, method="literal_ignore_case_v1"):
    sources, scopes = [], {}
    for source in data["sources"]:
        identifier = source["id"]
        encoded = source["text"].encode("utf-8")
        record = {
            "source_id": identifier,
            "title": "Synthetic retrieval fixture",
            "uri_or_path": "synthetic:" + identifier,
            "content_hash": hashlib.sha256(encoded).hexdigest(),
            **source.get("metadata", {}),
        }
        sources.append(SearchSource(record, source["text"]))
        for locator, text in source["scopes"].items():
            key = (identifier, locator)
            if key in scopes:
                raise ValueError("duplicate fixture scope")
            scopes[key] = (record["content_hash"], text)
    snapshot = SearchSnapshot(
        0, sum(len(source.text.encode("utf-8")) for source in sources), tuple(sources)
    )
    rows, totals, quote_count = [], [0, 0, 0], 0
    started = perf_counter()
    seen = set()
    for query in data["queries"]:
        if query["id"] in seen:
            raise ValueError("duplicate query ID")
        seen.add(query["id"])
        gold = {tuple(ref) for ref in query["relevant"]}
        if not gold <= scopes.keys():
            raise ValueError("gold reference outside fixture")
        response = retrieve(
            "retrieval-eval",
            FileSearchRequest(query=query["query"], limit=data["k"]),
            snapshot,
        )
        refs = []
        for hit in response["hits"]:
            key = (hit["source_id"], hit["locator"])
            if key not in scopes:
                raise ValueError("retrieved reference outside fixture")
            expected_hash, text = scopes[key]
            if (
                hit["content_hash"] != expected_hash
                or not hit["quote"]
                or hit["quote"] not in text
            ):
                raise ValueError("retrieved quote/hash does not match fixture scope")
            refs.append(key)
            quote_count += 1
        if len(refs) > data["k"] or len(set(refs)) != len(refs):
            raise ValueError("retrieved references violate top-k contract")
        metrics = score(refs, gold)
        for index, field in enumerate(
            ("true_positive", "false_positive", "false_negative")
        ):
            totals[index] += metrics[field]
        rows.append(
            {
                "id": query["id"],
                "category": query["category"],
                **metrics,
                "retrieved": [list(ref) for ref in refs],
            }
        )
    tp, fp, fn = totals
    return {
        "schema_version": 1,
        "scope": "synthetic_search_kernel_only",
        "method": method,
        "k": data["k"],
        "sources": len(sources),
        "queries": rows,
        "micro_precision": tp / (tp + fp) if tp + fp else None,
        "micro_recall": tp / (tp + fn) if tp + fn else None,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "verified_quotes": quote_count,
        "elapsed_seconds": perf_counter() - started,
        "model_calls": 0,
        "external_requests": 0,
        "provider_cost": None,
        "independent_review": False,
    }


def main():
    raw = FIXTURE.read_bytes()
    result = evaluate(json.loads(raw))
    result["fixture_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
