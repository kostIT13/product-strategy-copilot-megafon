"""Structural checks do not establish semantic entailment or source truthfulness."""
from dataclasses import asdict
import hashlib
from product_strategy_agent.domain.decisions.selection import fingerprint


def check_claim(claim, sources, project_id):
    issues, evidence = [], []
    if claim.project_id != project_id or claim.claim_type != "fact" or claim.status != "active":
        issues.append("claim_not_active_fact")
    if not claim.evidence:
        issues.append("claim_has_no_evidence")
    for ref in sorted(claim.evidence, key=lambda item: (str(item.source_id), item.source_revision, item.locator, item.quote)):
        row = sources.get((ref.source_id, ref.source_revision))
        errors = []
        metadata = None
        if row is None or row.project_id != project_id:
            errors.append("source_missing_in_project")
        else:
            metadata = {key: value for key, value in asdict(row).items() if key != "extracted_text"}
            if row.revision != ref.source_revision or row.latest_revision != ref.source_revision:
                errors.append("source_revision_stale")
            if row.status != "extracted":
                errors.append("source_not_extracted")
            if row.extracted_text is None:
                errors.append("source_exceeds_check_limit")
            elif hashlib.sha256(row.extracted_text.encode("utf-8")).hexdigest() != row.content_hash:
                errors.append("source_hash_mismatch")
            elif not ref.quote.strip() or ref.quote not in row.extracted_text:
                errors.append("quote_not_found")
            # Narrower fragment locators need a real fragment index before they can be verified.
            if not ref.locator.strip() or ref.locator != row.locator:
                errors.append("locator_not_verified")
        evidence.append({"reference": asdict(ref), "source": metadata, "blockers": errors})
        issues.extend(errors)
    canonical = asdict(claim)
    canonical["evidence"] = sorted(canonical["evidence"], key=lambda item: (str(item["source_id"]), item["source_revision"], item["locator"], item["quote"]))
    return {"claim": canonical, "claim_fingerprint": fingerprint(canonical),
            "evidence": evidence, "blockers": sorted(set(issues))}


def check_candidate(candidate, snapshot):
    capabilities = {item.id: item for item in snapshot.capabilities if item.project_id == snapshot.project_id}
    claims = {item.id: item for item in snapshot.claims if item.project_id == snapshot.project_id}
    sources = {(item.source_id, item.revision): item for item in snapshot.sources}
    checks, blockers = [], []
    for support in candidate.support:
        capability = capabilities.get(support.capability_id)
        errors, claim_checks = [], []
        if capability is None:
            errors.append("capability_missing_in_project")
        elif capability.status != "available":
            errors.append("capability_not_available")
        for claim_id in support.claim_ids:
            claim = claims.get(claim_id)
            if claim is None:
                checked = {"claim_id": str(claim_id), "blockers": ["claim_missing_in_project"]}
            else:
                checked = check_claim(claim, sources, snapshot.project_id)
            if capability is not None and claim_id not in capability.claim_ids:
                checked["blockers"] = sorted(set([*checked["blockers"], "claim_not_linked_to_capability"]))
            claim_checks.append(checked)
            errors.extend(checked["blockers"])
        cap_snapshot = asdict(capability) if capability else None
        if cap_snapshot:
            # Only selected links belong to this review; reader need not expose unrelated registry links.
            cap_snapshot["claim_ids"] = sorted((str(item) for item in capability.claim_ids if item in support.claim_ids))
        checks.append({"capability_id": str(support.capability_id),
            "capability": cap_snapshot, "claims": claim_checks,
            "blockers": sorted(set(errors))})
        blockers.extend(errors)
    return {"key": candidate.key, "text": candidate.text, "support": checks,
            "structural_status": "blocked" if blockers else "eligible_for_human_review",
            "blockers": sorted(set(blockers)), "requires_semantic_review": True,
            "publication_approved": False, "customer_promise_approved": False}
