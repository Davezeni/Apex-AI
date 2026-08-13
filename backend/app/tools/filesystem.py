"""Filesystem tools, all confined to the workspace root."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool, ToolContext, ToolError, ToolResult


def resolve_within(root: Path, rel: str) -> Path:
    """Resolve a path inside root, refusing traversal outside it."""
    if not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        raise ToolError(f"invalid path {rel!r} (must be relative, no '..')")
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ToolError(f"path escapes workspace root: {rel!r}")
    return p


def _require_str(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str):
        raise ToolError(f"{key!r} must be a string")
    return value


class WriteFileTool(Tool):
    name = "write_file"
    description = "Create or overwrite a file in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace root"},
            "content": {"type": "string", "description": "Full file contents"},
        },
        "required": ["path", "content"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = _require_str(args, "path")
        content = _require_str(args, "content")
        target = resolve_within(ctx.workspace_root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, summary=f"wrote {path}", content=f"wrote {path}")


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file in the workspace."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = _require_str(args, "path")
        target = resolve_within(ctx.workspace_root, path)
        if not target.is_file():
            return ToolResult(ok=False, summary=f"not found: {path}")
        return ToolResult(ok=True, summary=f"read {path}", content=target.read_text(encoding="utf-8"))


class ListFilesTool(Tool):
    name = "list_files"
    description = "List files and directories under a path (defaults to root)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory to list (optional)"}},
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        base = resolve_within(ctx.workspace_root, args.get("path") or ".")
        if not base.is_dir():
            return ToolResult(ok=False, summary=f"not a directory: {args.get('path')}")

        lines: list[str] = []
        for p in sorted(base.rglob("*")):
            rel = p.relative_to(ctx.workspace_root)
            lines.append(f"{'[D]' if p.is_dir() else '[F]'} {rel}")
        content = "\n".join(lines) if lines else "(empty)"
        return ToolResult(ok=True, summary=f"listed {len(lines)} entries", content=content)


class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace the first occurrence of a string in a file."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = _require_str(args, "path")
        old_text = _require_str(args, "old_text")
        new_text = _require_str(args, "new_text")
        target = resolve_within(ctx.workspace_root, path)
        if not target.is_file():
            return ToolResult(ok=False, summary=f"not found: {path}")

        text = target.read_text(encoding="utf-8")
        if old_text not in text:
            return ToolResult(ok=False, summary=f"old_text not found in {path}")
        target.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return ToolResult(ok=True, summary=f"edited {path}")


class DeleteFileTool(Tool):
    name = "delete_file"
    description = "Delete a file or empty directory in the workspace."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = _require_str(args, "path")
        target = resolve_within(ctx.workspace_root, path)
        if not target.exists():
            return ToolResult(ok=False, summary=f"not found: {path}")
        if target.is_dir():
            target.rmdir()  # refuses non-empty dirs
        else:
            target.unlink()
        return ToolResult(ok=True, summary=f"deleted {path}")


class CreateStructureTool(Tool):
    name = "create_structure"
    description = (
        "Scaffold a nested directory/file structure in one call. Pass a nested "
        "object: string values become file contents, object values become directories."
    )
    parameters = {
        "type": "object",
        "properties": {
            "structure": {
                "type": "object",
                "description": "Nested map of path → file-content (str) or sub-directory (object)",
            }
        },
        "required": ["structure"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        structure = args.get("structure")
        if not isinstance(structure, dict):
            raise ToolError("'structure' must be an object")

        created: list[str] = []

        def walk(node: dict, base: Path) -> None:
            for name, value in node.items():
                if not isinstance(name, str):
                    raise ToolError("structure keys must be strings")
                target = resolve_within(base, name)
                if isinstance(value, str):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(value, encoding="utf-8")
                    created.append(str(target.relative_to(ctx.workspace_root)))
                elif isinstance(value, dict):
                    target.mkdir(parents=True, exist_ok=True)
                    walk(value, target)
                else:
                    raise ToolError(f"invalid value for {name!r} (must be str or object)")

        walk(structure, ctx.workspace_root)
        return ToolResult(
            ok=True,
            summary=f"created {len(created)} file(s)",
            content="\n".join(created),
        )
