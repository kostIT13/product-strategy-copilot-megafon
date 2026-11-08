"""Deterministic portable artifacts; internal acceptance never authorizes publication."""
import hashlib
import json


def strategy_export(receipt):
    snapshot = receipt["review_snapshot"]
    draft = snapshot["draft"]
    header = ("INTERNAL REVIEW ONLY — hypotheses remain unverified.\n"
              "Publication and customer promises are NOT approved.\n"
              f"Approval: {receipt['id']}\nStrategy run: {snapshot['strategy_run_id']}\n"
              f"Decision: {draft['decision_id']}\nPreview SHA-256: {snapshot['preview_hash']}\n")

    def document(title, data):
        # Indented JSON keeps untrusted text as data rather than executable Markdown/HTML.
        body = json.dumps({"content": data, "gaps": draft["gaps"], "caveats": draft["caveats"]},
                          ensure_ascii=False, indent=2, sort_keys=True)
        return f"# {title}\n\n{header}\n" + "\n".join("    " + line for line in body.splitlines()) + "\n"

    files = {"strategy.md": document("Product strategy — internal", draft["product_strategy"]),
             "communication.md": document("Communication hypotheses — internal", draft["communication"]),
             "experiments.md": document("Experiment proposals — internal", draft["experiments"]),
             "review.json": json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"}
    return {"format_version": 1, "approval_id": receipt["id"], "scope": "internal_review",
            "publication_approved": False, "customer_promises_approved": False,
            "files": {name: {"content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
                      for name, content in files.items()}}
