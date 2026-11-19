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
| Codex App Server | 0.169.0-alpha.11.1 | Windows 10.0.26200 x86_64; Python 3.12; FastMCP 4.1.6 | Pass; discovered separate allowlists of four and eleven tools over stdio | Read-only and mutation scenarios passed | 2026-11-18. Separate local process with per-process configuration and an ephemeral session. |
| Codex desktop chat | — | Windows; Python 3.12; FastMCP 4.1.6 | Pass; the configured project server exposed four read tools | All four direct calls matched the previous CLI run | 2026-11-19. Verified tool-call trace on a copy of the completed pickup-window case. |
| Qwen Code | 0.25.2 | Windows; launcher confirmed on 2026-11-18 | Out of scope | Out of scope | Launcher version only. Connection guidance is available. |
| SourceCraft / Claude Code / Cursor / other IDEs | — | Connection guidance | Out of scope | Out of scope | Use the relevant instructions in [IDE instructions](ide-instructions.md). |

## File portability preflight

On 2026-11-18, a fresh synthetic pickup-window case was prepared in the active Codex session and copied to another project root. Separate CLI processes resumed at the same stage, loaded instruction bundle 1.1.13, and reproduced the verified quotes, option readiness and CSV sum. An exact import UUID replay and the read-only commands preserved every case file byte for byte. A local FastMCP SDK connection returned matching table and option JSON from the copy. Live host parity and actual human gates remain separate checks.

## Completion rule

M8 passed for the team's Codex workflow on 2026-11-19. The installed App Server passed the read and write parity scenarios, and a regular desktop chat discovered and called the four configured project tools directly.

The desktop chat initially had no PSA tools in its inventory. They became available during discovery. The trace records all four completed calls. Status reported `completed` at version 22. Validate and verify reported no errors, and coverage matched the CLI's nine paragraphs and promise preflight hash. All 282 case files matched the original after the run. Codex did not surface an approval prompt for these calls.

The local project configuration is in the ignored `.codex/config.toml`. To disable this server, set `enabled = false` under `[mcp_servers.psa]`, then reload the project in Codex and check the tool inventory.

The 2026-11-18 App Server run used the installed Codex binary's generated protocol schema. The client called `mcpServerStatus/list` and `mcpServer/tool/call` directly, with no model turn. Codex started `python -m product_strategy_agent.mcp_server` over stdio. The project ID, status, mode and workflow version matched the CLI. Validate and verify passed in both interfaces, and the complete coverage JSON matched, including nine checked paragraphs and the promise preflight hash. All 282 files in the synthetic case copy retained their SHA-256 hashes. Cyrillic was intact in the returned JSON despite garbled terminal display. The application's persistent MCP settings were untouched.

The write comparison used separate CLI and MCP roots with identical CSV fixtures. Both interfaces produced source ID `S-D6F59B3DB4CD`, claim `C-001` at `line:2` with the quote `renewed,10`, options `O-001` through `O-003`, and fixture decision `D-001`. On the second pair, both interfaces recorded revision `SRC-REV-0001` and identified the same affected claim and fixture decision. The pending count went from one to zero after the fixture review. Validate and verify passed on both pairs. Comparison excluded timestamps. CLI stores the revision event separately while the FastMCP import response also includes it. Test actors were labelled as fixtures and no workflow gates were run.
