"""Exact citation checks shared by completion and deterministic pipeline review."""


class CitationValidationError(ValueError):
    pass


def validate_citations(answer, contexts):
    allowed = {(context["source_id"], context["revision"]): context for context in contexts}
    seen = set()
    for citation in answer.citations:
        context = allowed.get((str(citation.source_id), citation.revision))
        identity = (str(citation.source_id), citation.revision, citation.quote)
        if (context is None or citation.locator != context["locator"] or not citation.quote.strip()
                or citation.quote not in context["text"] or identity in seen):
            raise CitationValidationError("model citation is outside supplied evidence")
        seen.add(identity)
