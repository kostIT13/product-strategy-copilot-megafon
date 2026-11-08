# Coverage and promise checks

`psa coverage <project-id>` checks non-placeholder prose paragraphs in `drafts/product-strategy.md` and `drafts/communication-strategy.md`. `psa validate` includes the same check, and the strategy gate blocks when coverage errors remain.

Mark every substantive paragraph with at least one of these markers:

- `[C-001]` — supported by a claim in `claims.jsonl`; multiple claim markers are allowed.
- `[HYPOTHESIS]` — unverified interpretation or proposal.
- `[OPEN QUESTION]` — unresolved point that must remain visible.
- `[COMMITMENT: CAP-001]` — a customer-facing promise tied to an available product capability.

In the `Ключевое сообщение и подтверждение` section, a claim marker by itself is not enough for customer-facing copy: use a capability commitment, or explicitly mark draft language as a hypothesis/open question.

Create capabilities with the CLI after recording their supporting factual claim:

```powershell
psa capability add <project-id> --name "Offline export" --status available --claim C-014
psa capability add <project-id> --name "Scheduled reports" --status planned
```

Only `available` capabilities can support a commitment. They must cite at least one factual claim; the claim itself still needs `verify` to check its locator and quote. Planned and unavailable capabilities cannot be promised as available.

`capabilities.jsonl` is append-only. To change a capability's status, append a new capability record with the new status and update commitment markers to its new ID; old records remain as history. Coverage checking is structural: it makes traceability explicit, but does not judge whether a claim or hypothesis is true.
