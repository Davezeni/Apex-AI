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
    """Runtime dependencies handed to every tool.

    Optional collaborators (sandbox, GitHub client, knowledge base, vision,
    image generator) are `None` when not configured; tools must degrade
    gracefully in that case.
    """

    workspace_root: Path
    sandbox: Any = None
    github: Any = None
    knowledge: Any = None
    vision: Any = None
    image_gen: Any = None


class Tool(ABC):
    """Interface every capability must implement."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the arguments object

    @abstractmethod
    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        raise NotImplementedError
