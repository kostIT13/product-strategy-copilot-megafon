# MCP adapter

The optional MCP server exposes existing CLI operations over local stdio. It does not contain separate workflow or ledger logic.

## Install and launch

Install the package with its optional MCP dependency:

```powershell
python -m pip install -e ".[mcp]"
psa-mcp
```

The equivalent module command is `python -m product_strategy_agent.mcp_server`. The server uses stdio and waits for an MCP host; it does not print a startup banner to stdout. Logs belong on stderr so they cannot corrupt the protocol stream.

The repository tracks only the SDK major line (`mcp>=2,<3`). The official SDK v2 renamed its server class from `FastMCP` to `MCPServer`; this adapter uses the v2 import and keeps the same decorator-based tool style. See the [official Python SDK](https://github.com/modelcontextprotocol/python-sdk) and its [v2 migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md).

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
- `psa_add_source`, `psa_fetch_source`, `psa_list_sources`
- `psa_add_claim`, `psa_add_gap`, `psa_add_option`, `psa_add_decision`
- `psa_approve_stage`
- `psa_validate`, `psa_verify`, `psa_render`, `psa_critic_pack`
- `psa_usage_add`, `psa_usage_report`

`psa_fetch_source` performs a network request only when explicitly called. Tools write only inside the selected project workspace, except for caller-supplied input/output paths. The server has no delete, shell, or arbitrary command tool.

## Current limits

MCP is optional and the core CLI has no MCP dependency. The adapter is stdio-only; it does not start an HTTP service. The SDK is versioned by major line rather than a lock file because the default setup remains dependency-free. Host compatibility still needs a live connection check in each target IDE before relying on that host for a demo.
