"""Document authoring tool: generate SAD/SDD/PRD/README files."""

from __future__ import annotations

from typing import Any

from ..media import author
from .base import Tool, ToolContext, ToolResult
from .filesystem import resolve_within


class GenerateDocumentTool(Tool):
    name = "generate_document"
    description = (
        "Generate an engineering document (sad, sdd, prd, or readme) as Markdown "
        "in the workspace, filled from provided details."
    )
    parameters = {
        "type": "object",
        "properties": {
            "doc_type": {"type": "string", "description": "sad|sdd|prd|readme"},
            "title": {"type": "string"},
            "details": {
                "type": "object",
                "description": "Section content: overview, goals, context, components, stack, etc.",
            },
            "path": {"type": "string", "description": "Output path ending in .md"},
        },
        "required": ["doc_type", "title", "path"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        doc_type = args.get("doc_type")
        title = args.get("title")
        path = args.get("path")
        details = args.get("details") or {}

        if not isinstance(doc_type, str) or not isinstance(title, str) or not isinstance(path, str):
            return ToolResult(ok=False, summary="doc_type, title, path must be strings")
        if not isinstance(details, dict):
            return ToolResult(ok=False, summary="details must be an object")

        try:
            target = resolve_within(ctx.workspace_root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            author.write_document(doc_type, title, details, target)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"document generation failed: {exc}")
        return ToolResult(ok=True, summary=f"generated {path}", content=f"document saved to {path}")
