"""Chart generation tool."""

from __future__ import annotations

from typing import Any

from ..media import charts
from .base import Tool, ToolContext, ToolResult
from .filesystem import resolve_within


class GenerateChartTool(Tool):
    name = "generate_chart"
    description = (
        "Generate a chart (bar, line, pie, scatter, or histogram) as a PNG "
        "from label/value data, saved to the workspace. Use to visualize data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "labels": {"type": "array", "items": {"type": "string"}},
            "values": {"type": "array", "items": {"type": "number"}},
            "kind": {"type": "string", "description": "bar|line|pie|scatter|hist"},
            "title": {"type": "string"},
            "path": {"type": "string", "description": "Output path ending in .png"},
        },
        "required": ["labels", "values", "kind", "path"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        labels = args.get("labels")
        values = args.get("values")
        kind = args.get("kind")
        path = args.get("path")
        title = args.get("title") or ""

        if not isinstance(labels, list) or not isinstance(values, list):
            return ToolResult(ok=False, summary="labels and values must be lists")
        if not isinstance(kind, str) or not isinstance(path, str):
            return ToolResult(ok=False, summary="kind and path must be strings")
        if not path.lower().endswith(".png"):
            return ToolResult(ok=False, summary="path must end in .png")

        try:
            values = [float(v) for v in values]
            target = resolve_within(ctx.workspace_root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            charts.render_chart(
                [str(l) for l in labels], values, kind, target, title=title
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"chart failed: {exc}")
        return ToolResult(ok=True, summary=f"chart saved to {path}", content=f"chart saved to {path}")
