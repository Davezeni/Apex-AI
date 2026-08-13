"""Document tools: parse a file into markdown, and convert between formats."""

from __future__ import annotations

from typing import Any

from ..media import convert as converter
from .base import Tool, ToolContext, ToolResult
from .filesystem import resolve_within


class ParseDocumentTool(Tool):
    name = "parse_document"
    description = (
        "Parse a document (csv, xlsx, docx, txt, md, html, json) in the workspace "
        "and return its contents as Markdown. Use to read tabular or Office files."
    )
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not isinstance(path, str):
            return ToolResult(ok=False, summary="path must be a string")
        try:
            target = resolve_within(ctx.workspace_root, path)
            md = converter.to_markdown(target)
        except converter.ConversionError as exc:
            return ToolResult(ok=False, summary=str(exc))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"parse failed: {exc}")
        return ToolResult(ok=True, summary=f"parsed {path}", content=md)


class ConvertFileTool(Tool):
    name = "convert_file"
    description = (
        "Convert a file in the workspace to another format (csv, xlsx, md, txt, "
        "html). Copying data between file types (e.g. csv→xlsx) goes through "
        "Markdown and preserves table structure."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Existing file path"},
            "target": {"type": "string", "description": "Output path with new extension"},
        },
        "required": ["source", "target"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        source = args.get("source")
        target = args.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            return ToolResult(ok=False, summary="source and target must be strings")
        try:
            src = resolve_within(ctx.workspace_root, source)
            dst = resolve_within(ctx.workspace_root, target)
            dst.parent.mkdir(parents=True, exist_ok=True)
            converter.convert_file(src, dst)
        except converter.ConversionError as exc:
            return ToolResult(ok=False, summary=str(exc))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"conversion failed: {exc}")
        return ToolResult(ok=True, summary=f"converted {source} → {target}")
