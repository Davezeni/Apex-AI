"""Tests for filesystem tools, focusing on workspace-root confinement."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.router.schema import ToolCall
from app.tools.base import ToolContext, ToolError
from app.tools.filesystem import WriteFileTool, resolve_within
from app.tools.registry import ToolRegistry


@pytest.fixture
def ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(workspace_root=tmp_path)


@pytest.mark.asyncio
async def test_write_and_read(ctx):
    tool = WriteFileTool()
    result = await tool.execute(
        {"path": "src/app.py", "content": "print('hi')"}, ctx
    )
    assert result.ok
    assert (ctx.workspace_root / "src" / "app.py").read_text() == "print('hi')"


def test_traversal_rejected():
    root = Path("/tmp/ws")
    with pytest.raises(Exception):
        resolve_within(root, "../etc/passwd")
    with pytest.raises(Exception):
        resolve_within(root, "/etc/passwd")


@pytest.mark.asyncio
async def test_write_outside_root_rejected(ctx):
    registry = ToolRegistry()
    registry.register(WriteFileTool())
    result = await registry.execute(
        ToolCall(id="1", name="write_file", arguments={"path": "../../outside.txt", "content": "evil"}),
        ctx,
    )
    assert not result.ok
    assert not Path("/tmp/outside.txt").exists()
