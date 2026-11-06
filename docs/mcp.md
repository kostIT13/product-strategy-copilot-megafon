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
- `psa_add_source`, `psa_fetch_source`, `psa_list_sources`
- `psa_add_claim`, `psa_add_gap`, `psa_add_option`, `psa_add_decision`, `psa_add_capability`
- `psa_approve_stage`
- `psa_coverage`, `psa_validate`, `psa_verify`, `psa_render`, `psa_render_adopt_existing`, `psa_critic_pack`
- `psa_usage_add`, `psa_usage_report`

`psa_fetch_source` performs a network request only when explicitly called. Tools write only inside the selected project workspace, except for caller-supplied input/output paths. The server has no delete, shell, or arbitrary command tool.

## Current limits

MCP is optional and the core CLI has no MCP dependency. The adapter is stdio-only; it does not start an HTTP service. FastMCP is constrained to major version 4; the default setup remains dependency-free. Host compatibility still needs a live connection check in each target IDE before relying on that host for a demo.
