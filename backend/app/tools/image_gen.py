"""Image generation tool."""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolContext, ToolResult
from .filesystem import resolve_within


class GenerateImageTool(Tool):
    name = "generate_image"
    description = (
        "Generate an image from a text prompt and save it to the workspace "
        "(PNG). Use to create logos, illustrations, or UI mockups."
    )
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "path": {"type": "string", "description": "Output path, e.g. images/logo.png"},
        },
        "required": ["prompt", "path"],
    }

    def __init__(self, generator) -> None:
        self._gen = generator

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        prompt = args.get("prompt")
        path = args.get("path")
        if not isinstance(prompt, str) or not prompt.strip():
            return ToolResult(ok=False, summary="prompt must be a non-empty string")
        if not isinstance(path, str) or not path.lower().endswith(".png"):
            return ToolResult(ok=False, summary="path must end in .png")

        target = resolve_within(ctx.workspace_root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = await self._gen.generate(prompt)
            target.write_bytes(data)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"image generation failed: {exc}")
        return ToolResult(ok=True, summary=f"generated {path}", content=f"image saved to {path}")
