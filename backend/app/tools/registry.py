"""Tool registry: name → tool, plus JSON-Schema definitions for the model."""

from __future__ import annotations

from ..router.schema import ToolCall, ToolDef
from .base import Tool, ToolContext, ToolError, ToolResult


class ToolRegistry:
    """Holds registered tools and executes tool calls safely."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name!r}")
        self._tools[tool.name] = tool

    def definitions(self, allow: set[str] | None = None) -> list[ToolDef]:
        tools = self._tools.values()
        if allow is not None:
            tools = [t for t in tools if t.name in allow]
        return [
            ToolDef(name=t.name, description=t.description, parameters=t.parameters)
            for t in tools
        ]

    async def execute(self, call: ToolCall, ctx: ToolContext) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(ok=False, summary=f"unknown tool {call.name!r}")

        try:
            return await tool.execute(call.arguments, ctx)
        except ToolError as exc:
            return ToolResult(ok=False, summary=str(exc), content=str(exc))
        except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the model
            message = f"{type(exc).__name__}: {exc}"
            return ToolResult(ok=False, summary=message, content=message)
