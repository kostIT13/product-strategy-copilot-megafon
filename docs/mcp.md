# MCP adapter

The optional MCP server exposes existing CLI operations over local stdio. It does not contain separate workflow or ledger logic.

## Install and launch

Install the package with its optional MCP dependency:

```powershell
python -m pip install -e ".[mcp]"
psa-mcp
```

The equivalent module command is `python -m product_strategy_agent.mcp_server`. The server uses stdio and waits for an MCP host; it does not print a startup banner to stdout. Logs belong on stderr so they cannot corrupt the protocol stream.

The optional dependency installs the standalone [FastMCP framework](https://gofastmcp.com/) from the `fastmcp>=4,<5` major line. The adapter creates a `FastMCP` server and runs it explicitly over stdio. The CLI and Python core remain usable without FastMCP.

## Host configuration

For hosts that accept the common `mcpServers` JSON shape, configure a local process:

```json
{
  "mcpServers": {
    "product-strategy-agent": {
      "command": "python",
      "args": ["-m", "product_strategy_agent.mcp_server"],
      "cwd": "ABSOLUTE_PATH_TO_REPOSITORY"
    }
  }
}
```

Use the Python executable from the environment where `product-strategy-agent[mcp]` is installed. Each host has its own config-file location and interpolation rules; adapt `cwd` and the executable path to that host. Keep the CLI as a full fallback.

## Exposed tools

- `psa_init`, `psa_status`, `psa_next`, `psa_mode_set`
- `psa_revisit`, `psa_revisit_resolve`
- `psa_add_source`, `psa_fetch_source`, `psa_list_sources`, `psa_search_sources`
- `psa_add_claim`, `psa_add_gap`, `psa_add_option`, `psa_add_decision`, `psa_add_capability`
- `psa_approve_stage`
- `psa_coverage`, `psa_validate`, `psa_verify`, `psa_render`, `psa_render_adopt_existing`, `psa_critic_pack`
- `psa_usage_add`, `psa_usage_report`
- `psa_check_promises` — [file draft promise/evidence preflight](file-promise-check.md), read-only and never approval
- `psa_check_strategy` — [required strategy sections](strategy-structure.md), read-only structural completeness and never semantic/publication approval
- `psa_check_validation_plan` — [measurement plan contract](validation-plan-contract.md), read-only schema/current baseline proof and never observed effect or experiment permission
- `psa_withdraw_claim`, `psa_claim_impact` — [human withdrawal/effective evidence](claim-withdrawal.md), immutable history and derived review without changing human decisions
- `psa_correct_claim` — [attributed correction](claim-correction.md), append replacement with current citations and workflow v5 recovery; preserves original claims and human decisions
- `psa_review_workflow`, `psa_reopen_workflow` — [review/reopen](workflow-reopen.md): reviewed snapshot, explicit human instruction, selected stage reset, preserved history and fresh gates
- `psa_withdraw_source`, `psa_source_impact` — [source withdrawal](source-withdrawal.md): attributed v6 journal operation, dependent evidence review and no automatic reactivation

`psa_fetch_source` performs a network request only when explicitly called. Tools write only inside the selected project workspace, except for caller-supplied input/output paths. The server has no delete, shell, or arbitrary command tool.

`psa_search_sources` is a read-only local operation over current hash-checked text, with exact quote/locator references and explicit truncation. It does not fetch URLs or call a model. See the [file search contract](file-source-search.md) for limits and differences from legacy FTS.

## Current limits

MCP is optional and the core CLI has no MCP dependency. The adapter is stdio-only; it does not start an HTTP service. FastMCP is constrained to major version 4; the default setup remains dependency-free. Host compatibility still needs a live connection check in each target IDE before relying on that host for a demo.
