"""MCP (Model Context Protocol) client.

Lets Apex AI use tools from external MCP servers (databases, filesystems,
browsers, etc.) as if they were native tools. Servers are configured in
config.yaml and connected over stdio. The integration is optional and
degrade-graceful: any server that fails to start is skipped, never fatal.

Each MCP server's tools are exposed to the agent under a namespaced name:
`mcp_<server>_<tool>`.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from ..tools.base import Tool, ToolContext, ToolResult

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    _HAS_MCP = True
except Exception:  # pragma: no cover — mcp optional at runtime
    _HAS_MCP = False


def mcp_available() -> bool:
    return _HAS_MCP


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class MCPToolAdapter(Tool):
    """Wraps an MCP tool as a native Apex AI tool."""

    def __init__(self, connection: "MCPServerConnection", mcp_name: str,
                 description: str, input_schema: dict[str, Any]) -> None:
        self.name = f"mcp_{connection.name}_{mcp_name}"
        self.description = description or f"MCP tool '{mcp_name}' from {connection.name}"
        self.parameters = input_schema or {"type": "object", "properties": {}}
        self._conn = connection
        self._mcp_name = mcp_name

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        del ctx
        try:
            result = await self._conn.call_tool(self._mcp_name, args or {})
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"mcp {self._mcp_name} failed: {exc}")

        text = self._extract_text(result)
        return ToolResult(ok=True, summary=f"mcp {self._mcp_name}", content=text or "(no text output)")

    @staticmethod
    def _extract_text(result: Any) -> str:
        parts: list[str] = []
        for block in getattr(result, "content", []) or []:
            t = getattr(block, "type", None)
            if t == "text":
                parts.append(getattr(block, "text", ""))
            else:
                # serialize non-text blocks (images/resources) minimally
                data = getattr(block, "model_dump", None)
                if callable(data):
                    parts.append(str(data()))
        return "\n".join(p for p in parts if p)


class MCPServerConnection:
    """A long-lived stdio connection to one MCP server."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.name = config.name
        self._params = StdioServerParameters(
            command=config.command, args=config.args, env=config.env or None
        )
        self._stack: contextlib.AsyncExitStack | None = None
        self._session: Any = None

    async def start(self) -> list[MCPToolAdapter]:
        if not _HAS_MCP:
            return []
        self._stack = contextlib.AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(self._params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        tools_result = await self._session.list_tools()

        adapters: list[MCPToolAdapter] = []
        for tool in tools_result.tools:
            schema = _to_json_schema(tool.input_schema)
            adapters.append(
                MCPToolAdapter(self, tool.name, tool.description or "", schema)
            )
        return adapters

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._session is None:
            raise RuntimeError(f"MCP server {self.name} not connected")
        return await self._session.call_tool(name, arguments)

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None


def _to_json_schema(input_schema: Any) -> dict[str, Any]:
    """Convert an MCP input schema (Pydantic model or dict) to a JSON Schema."""
    if input_schema is None:
        return {"type": "object", "properties": {}}
    if isinstance(input_schema, dict):
        return input_schema
    if hasattr(input_schema, "model_json_schema"):
        return input_schema.model_json_schema()
    if hasattr(input_schema, "dict"):
        return input_schema.dict()
    return {"type": "object", "properties": {}}


class MCPManager:
    """Connects to all configured MCP servers and exposes their tools."""

    def __init__(self, servers: list[MCPServerConfig]) -> None:
        self._servers = servers
        self._connections: list[MCPServerConnection] = []

    @property
    def available(self) -> bool:
        return _HAS_MCP and bool(self._servers)

    async def start(self) -> list[MCPToolAdapter]:
        """Connect to servers, returning all their tools. Failures are skipped."""
        if not _HAS_MCP:
            return []
        adapters: list[MCPToolAdapter] = []
        for cfg in self._servers:
            conn = MCPServerConnection(cfg)
            try:
                tools = await conn.start()
                adapters.extend(tools)
                self._connections.append(conn)
            except Exception:  # noqa: BLE001 — skip unavailable servers
                await conn.close()
        return adapters

    async def close(self) -> None:
        for conn in self._connections:
            await conn.close()
        self._connections = []
