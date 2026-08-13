"""Tool base classes and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """The outcome of a tool execution."""

    ok: bool = True
    summary: str = ""  # human/UI-facing one-liner
    content: str = ""  # text returned to the model as the tool result
    detail: dict[str, Any] = field(default_factory=dict)


class ToolError(Exception):
    """A handled tool failure (message is surfaced to the model)."""


@dataclass
class ToolContext:
    """Runtime dependencies handed to every tool."""

    workspace_root: Path


class Tool(ABC):
    """Interface every capability must implement."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the arguments object

    @abstractmethod
    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        raise NotImplementedError
