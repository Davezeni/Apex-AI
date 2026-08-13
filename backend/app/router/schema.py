"""Normalized types shared by providers and the agent loop.

Every provider adapter translates its native request/response into these
types, so the agent loop and router are provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ToolDef:
    """A tool definition exposed to the model (name + JSON Schema)."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]
    # Gemini 3.x thinking-mode requires echoing back this signature on the
    # functionCall part. Preserved so multi-turn tool use works.
    thought_signature: str | None = None


@dataclass
class Message:
    """A normalized chat message."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class GenerateRequest:
    """A normalized generation request to any provider."""

    messages: list[Message]
    tools: list[ToolDef] = field(default_factory=list)
    model: str | None = None  # set by the router from the pool entry
    max_tokens: int = 4096
    temperature: float = 0.2


@dataclass
class GenerateResponse:
    """A normalized generation response from any provider."""

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Optional chain-of-thought / reasoning emitted by reasoning models.
    reasoning: str | None = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)
