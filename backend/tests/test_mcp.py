"""Tests for the MCP client (graceful degradation; no network required)."""

from __future__ import annotations

import pytest

from app.mcp.client import MCPManager, MCPServerConfig, mcp_available


def test_mcp_availability_flag():
    assert mcp_available() in (True, False)  # depends on install; must be a bool


def test_empty_manager_not_available():
    m = MCPManager([])
    assert m.available is False


@pytest.mark.asyncio
async def test_bad_server_skipped_gracefully():
    m = MCPManager([MCPServerConfig(name="bad", command="definitely-not-a-real-cmd", args=[])])
    tools = await m.start()
    assert tools == []  # skipped, not raised
    await m.close()


def test_json_schema_conversion():
    from app.mcp.client import _to_json_schema

    assert _to_json_schema(None) == {"type": "object", "properties": {}}
    d = {"type": "object", "properties": {"x": {"type": "string"}}}
    assert _to_json_schema(d) == d


def test_tool_adapter_namespacing():
    from app.mcp.client import MCPToolAdapter

    # Minimal fake connection with the required attributes.
    class FakeConn:
        name = "db"

        async def call_tool(self, name, args):
            return None

    adapter = MCPToolAdapter(FakeConn(), "query", "Run a query", {"type": "object"})
    assert adapter.name == "mcp_db_query"
    assert adapter.parameters == {"type": "object"}
