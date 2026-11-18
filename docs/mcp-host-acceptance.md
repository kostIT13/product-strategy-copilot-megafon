# FastMCP host acceptance

This checklist records the live Codex stdio connection and CLI/MCP parity required by MVP item M8. Codex is the team’s primary IDE and the only host in the current acceptance scope. Connection instructions remain available for other IDEs as compatibility guidance. The adapter is implemented in `src/product_strategy_agent/mcp_server.py`; implementation alone does not count as host acceptance.

## Common setup

Run from a clean checkout in a dedicated Python environment:

```powershell
python -m pip install -e ".[mcp]"
python -c "from fastmcp import FastMCP; print('FastMCP import: OK')"
```

Configure the host to start `python -m product_strategy_agent.mcp_server` with the repository as its working directory and the same Python environment. Use the host's own supported configuration mechanism; do not assume every host accepts the same JSON shape. Restart/reload the host, confirm the process connects over stdio, and inspect its discovered tool list.

## Parity scenario

Use fresh disposable project IDs in Codex and run the same operations through both CLI and MCP. Compare returned IDs, status, and validation outcomes; timestamps and JSON key order may differ.

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
| Local MCP SDK client (not an IDE host) | MCP Python SDK 2.3.0 | Windows; Python 3.12; FastMCP 4.1.6 | Pass; 20 tools discovered over stdio | Partial: revisit mutation via MCP; validate, verify, and revisit readout matched through CLI | `projects/mcp-host-smoke-20261106/`; 2026-11-06. Does not establish Codex UI integration |
| Codex | — | Current workspace; FastMCP 4.1.6 installed in local `.venv` | Not run | Not run | Requires a live configured Codex host session |
| Qwen Code | 0.25.2 | Windows; launcher confirmed on 2026-11-18 | Out of scope | Out of scope | Launcher version only. Connection guidance is available. |
| SourceCraft / Claude Code / Cursor / other IDEs | — | Connection guidance | Out of scope | Out of scope | Use the relevant instructions in [IDE instructions](ide-instructions.md). |

## File portability preflight

On 2026-11-18, a fresh synthetic pickup-window case was prepared in the active Codex session and copied to another project root. Separate CLI processes resumed at the same stage, loaded instruction bundle 1.1.13, and reproduced the verified quotes, option readiness and CSV sum. An exact import UUID replay and the read-only commands preserved every case file byte for byte. A local FastMCP SDK connection returned matching table and option JSON from the copy. Live host parity and actual human gates remain separate checks.

## Completion rule

M8 remains open until Codex has a live stdio connection and matching CLI/MCP results for the parity scenario. Package installation and local SDK checks are preflights.
