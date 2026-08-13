"""Agent event types streamed to the client (and later, the WebSocket)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextDelta:
    delta: str


@dataclass(frozen=True)
class Thinking:
    """Chain-of-thought / reasoning text from the model."""

    text: str


@dataclass(frozen=True)
class ToolCallEvent:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResultEvent:
    name: str
    ok: bool
    summary: str
    duration_seconds: float = 0.0
    # Extra structured info (exit code, stdout/stderr, command, etc.).
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Done:
    text: str


@dataclass(frozen=True)
class Review:
    """A critique of the work, produced by a separate reviewer agent."""

    text: str


@dataclass(frozen=True)
class Error:
    message: str


AgentEvent = TextDelta | Thinking | ToolCallEvent | ToolResultEvent | Done | Review | Error
