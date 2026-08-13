"""Command-line smoke test: run one agent turn without a server.

Usage:
    python -m cli "create a hello.py that prints hi"
"""

from __future__ import annotations

import asyncio
import sys

from app.agent.events import Done, Error, Review, TextDelta, ToolCallEvent, ToolResultEvent
from app.agent.orchestrator import Orchestrator
from app.config import load_settings
from app.container import (
    build_adapters,
    build_router,
    build_tool_context,
    build_tools,
)


async def main() -> None:
    message = sys.argv[1] if len(sys.argv) > 1 else "Say hello in one sentence."
    settings = load_settings()
    router = build_router(settings, build_adapters(settings))
    tools = build_tools(settings)
    ctx = build_tool_context(settings)
    orchestrator = Orchestrator(router, tools, ctx, max_iterations=settings.max_iterations)

    async def emit(event) -> None:
        if isinstance(event, TextDelta):
            print(event.delta, end="", flush=True)
        elif isinstance(event, ToolCallEvent):
            print(f"\n[TOOL] {event.name} {event.arguments}")
        elif isinstance(event, ToolResultEvent):
            print(f"[RESULT] {'ok' if event.ok else 'FAIL'} — {event.summary}")
        elif isinstance(event, Review):
            print(f"\n\n[REVIEW]\n{event.text}")
        elif isinstance(event, Done):
            print(f"\n\n{event.text}")
        elif isinstance(event, Error):
            print(f"\n[ERROR] {event.message}")

    await orchestrator.run(message, emit=emit)


if __name__ == "__main__":
    asyncio.run(main())
