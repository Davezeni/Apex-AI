"""Vision tools: describe an image and extract text (OCR) from it."""

from __future__ import annotations

from typing import Any

from ..media.vision import mime_for
from .base import Tool, ToolContext, ToolResult
from .filesystem import resolve_within


class DescribeImageTool(Tool):
    name = "describe_image"
    description = "Describe the contents of an image file in the workspace."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def __init__(self, vision) -> None:
        self._vision = vision

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not isinstance(path, str):
            return ToolResult(ok=False, summary="path must be a string")
        try:
            target = resolve_within(ctx.workspace_root, path)
            if not target.is_file():
                return ToolResult(ok=False, summary=f"not found: {path}")
            data = target.read_bytes()
            description = await self._vision.describe(data, mime_for(path))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"vision failed: {exc}")
        return ToolResult(ok=True, summary=f"described {path}", content=description)


class OcrImageTool(Tool):
    name = "ocr_image"
    description = "Extract all text from an image file (OCR)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def __init__(self, vision) -> None:
        self._vision = vision

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not isinstance(path, str):
            return ToolResult(ok=False, summary="path must be a string")
        try:
            target = resolve_within(ctx.workspace_root, path)
            if not target.is_file():
                return ToolResult(ok=False, summary=f"not found: {path}")
            data = target.read_bytes()
            text = await self._vision.extract_text(data, mime_for(path))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"OCR failed: {exc}")
        return ToolResult(ok=True, summary=f"OCR done for {path}", content=text)
