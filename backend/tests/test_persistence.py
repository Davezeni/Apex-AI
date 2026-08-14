"""Tests for workspace persistence and context injection."""

from __future__ import annotations

from pathlib import Path

from app.workspace.persistence import build_workspace_persistence


def test_no_supabase_returns_none(tmp_path: Path):
    p = build_workspace_persistence("sqlite", None, None, tmp_path)
    assert p is None


def test_supabase_requires_keys(tmp_path: Path):
    # store_backend=supabase but missing keys -> None (graceful)
    p = build_workspace_persistence("supabase", None, None, tmp_path)
    assert p is None


def test_workspace_context_injection():
    from app.agent.core import Agent
    from app.router.router import ModelRouter
    from app.tools.base import ToolContext
    from app.tools.registry import ToolRegistry

    root = Path("/tmp/apex_ctx_test")
    root.mkdir(exist_ok=True)
    (root / "app.py").write_text("print('hello')\n" * 5)
    (root / "index.html").write_text("<h1>hi</h1>")

    agent = Agent(ModelRouter.__new__(ModelRouter), ToolRegistry(), ToolContext(workspace_root=root))
    ctx = agent._workspace_context()
    assert ctx is not None
    assert "app.py" in ctx and "index.html" in ctx
    assert "print('hello')" in ctx  # contents included

    # memory file is empty -> None
    assert agent._memory_file() is None
    (root / "apex_memory.md").write_text("user prefers Python")
    assert agent._memory_file() == "user prefers Python"

    import shutil
    shutil.rmtree(root, ignore_errors=True)
