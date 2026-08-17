"""
mcp_client_test.py -- the client side of MCP, for real this time.
Earlier we tested mcp_server.py by connecting to it in the SAME running
program, a shortcut for testing. This file is different: it actually
launches mcp_server.py as its own separate process and talks to it purely
through the MCP protocol, over stdin and stdout, the same experience as
connecting to someone else's MCP server, like weather-mcp, would be.
"""
import asyncio
import sys

from mcp import client
from mcp.client.stdio import StdioServerParameters, stdio_client

# This describes HOW to start the other program, not a connection to it
# yet. "command" is the program to run, "args" are the arguments to give
# it, exactly like typing this in a terminal yourself:
#   ../.venv/bin/python mcp_server.py
params = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server.py"],
)


async def main():
    # stdio_client(params) actually starts mcp_server.py as a real,
    # separate process right here, and hands us a live connection to its
    # stdin and stdout. Client wraps that connection so we can speak MCP
    # over it, list tools, call tools, without touching stdin/stdout by
    # hand ourselves.
    async with client.Client(stdio_client(params)) as c:
        tools = await c.list_tools()
        print("Connected to a real, separate process. Tools it offers:")
        for tool in tools.tools:
            print(f" - {tool.name}: {tool.description}")

        print()
        result = await c.call_tool("geocode", {"city_name": "Chicago"})
        print("Real result, sent back over the actual protocol:")
        print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
