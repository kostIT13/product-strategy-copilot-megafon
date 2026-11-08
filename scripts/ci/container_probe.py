"""Read-only startup probe: non-root process and real main FastMCP inventory."""
import asyncio
import json
import os

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def main():
    if os.getuid() == 0:
        raise ValueError("container must run as a non-root user")
    async with Client(StdioTransport(command="psa-main-mcp", args=[], keep_alive=False), timeout=30) as client:
        tools = await client.list_tools()
        if len(tools) != 9:
            raise ValueError("unexpected main MCP inventory")
    print(json.dumps({"ok": True, "uid": os.getuid(), "mcp_tools": len(tools), "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())
