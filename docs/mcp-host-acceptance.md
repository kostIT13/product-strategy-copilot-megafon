# FastMCP host acceptance

This checklist records the live stdio connection and CLI/MCP parity required by MVP item M8. The adapter is implemented in `src/product_strategy_agent/mcp_server.py`; implementation alone does not count as host acceptance.

## Common setup

Run from a clean checkout in a dedicated Python environment:

```powershell
python -m pip install -e ".[mcp]"
python -c "from fastmcp import FastMCP; print('FastMCP import: OK')"
```

Configure the host to start `python -m product_strategy_agent.mcp_server` with the repository as its working directory and the same Python environment. Use the host's own supported configuration mechanism; do not assume every host accepts the same JSON shape. Restart/reload the host, confirm the process connects over stdio, and inspect its discovered tool list.

## Parity scenario

Use a fresh disposable project ID per host and run the same operations through both CLI and MCP. Compare returned IDs, status, and validation outcomes; timestamps and JSON key order may differ.

1. Initialize a project (`psa init` / `psa_init`) and read its status (`status` / `psa_status`).
2. Import the same synthetic source and add an evidence-linked claim; compare source/claim IDs and stored locator/quote.
3. Add the three option roles and a decision; confirm both paths accept equivalent arguments and resolve the same IDs.
4. Run validate and verify through each interface; compare pass/fail and reported errors.
5. On a separate disposable project, re-import a changed source, list revisit items, resolve review, and confirm no pending items remain.
6. Record any host-specific tool-name, argument-schema, timeout, working-directory, or stdio logging issue.

Do not point the mutation steps at `projects/demo` or another user's project. The scenario uses only `evals/revisit-demo/` synthetic CSV fixtures.

## Host record

Complete a row only after a live connection and the parity scenario have been observed. Record exact host and version, OS, Python version, FastMCP version, date, result, and evidence (sanitized logs or screenshots). Leave unknown details blank rather than infer them.

| Host | Host version | Environment | Connection | Parity | Evidence / limitation |
|---|---|---|---|---|---|
| Codex | — | Current workspace; FastMCP unavailable | Not run | Not run | Needs dependency and a live configured host session |
| Qwen Coder | — | Not available in this workspace | Not run | Not run | Requires access to target host |
| SourceCraft | — | Not available in this workspace | Not run | Not run | Requires access to target host |

## Completion rule

M8 remains open until the required target hosts have live stdio connections and matching results for the common scenario, or the MVP plan explicitly narrows its target-host scope. A successful import or package installation alone is not a pass.
