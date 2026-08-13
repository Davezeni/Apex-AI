"""Agent event types streamed to the client (and later, the WebSocket)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextDelta:
    delta: str


@dataclass(frozen=True)
class ToolCallEvent:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResultEvent:
    name: str
    ok: bool
    summary: str


@dataclass(frozen=True)
class Done:
    text: str


@dataclass(frozen=True)
class Error:
    message: str


AgentEvent = TextDelta | ToolCallEvent | ToolResultEvent | Done | Error
