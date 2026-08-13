"""The agent loop: reason → act → observe → repeat.

A single-agent implementation that emits events through a callback so the
caller (WebSocket, HTTP, or CLI) receives streaming text deltas and step
events in real time. Structured so additional agents can be added later via
an Agent Registry without changing this loop.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from ..router.router import ModelRouter
from ..router.schema import GenerateRequest, Message
from ..tools.registry import ToolContext, ToolRegistry
from .events import (
    AgentEvent,
    Done,
    Error,
    TextDelta,
    Thinking,
    ToolCallEvent,
    ToolResultEvent,
)

Emit = Callable[[AgentEvent], Awaitable[None]]

DEFAULT_SYSTEM_PROMPT = (
    "You are Apex AI, a senior software engineer embedded in a self-hosted "
    "builder. You build real, working software projects, not just snippets.\n\n"
    "When the user asks you to build an app, website, API, or service:\n"
    "1. PLAN first: state the structure you'll create in one or two lines.\n"
    "2. SCAFFOLD a proper project structure using create_structure — e.g. "
    "src/, a main entry file, README.md, config files, and a sensible folder "
    "layout for the chosen language.\n"
    "3. Write each file with write_file, keeping code complete and runnable.\n"
    "4. If a sandbox is available, run and verify with run_command; otherwise "
    "state clearly that it is untested.\n"
    "5. Explain what you built, how to run it, and what a user should see.\n\n"
    "Memory: you have access to the prior conversation history. Refer back to "
    "what the user said earlier and build on it — do not forget earlier "
    "context or re-ask what was already decided.\n\n"
    "Language: when not specified, choose the most appropriate language for "
    "the task (Python for data/APIs, JS/TS for web, etc.) and say why.\n\n"
    "Honesty: end with (1) what was DONE, (2) what is NOT done or untested, "
    "and (3) concrete next steps. Never imply unverified work succeeded."
)


async def _noop(event: AgentEvent) -> None:
    del event


class Agent:
    """Executes a bounded reasoning/acting loop over a model router + tools."""

    def __init__(
        self,
        router: ModelRouter,
        tools: ToolRegistry,
        ctx: ToolContext,
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = 12,
    ) -> None:
        self._router = router
        self._tools = tools
        self._ctx = ctx
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations

    async def run(
        self,
        user_message: str,
        history: list[Message] | None = None,
        emit: Emit | None = None,
    ) -> None:
        """Run one turn, emitting events as the agent thinks and acts."""

        emit = emit or _noop

        messages: list[Message] = [
            Message(role="system", content=self._system_prompt),
            *(history or []),
            Message(role="user", content=user_message),
        ]

        for _ in range(self._max_iterations):
            streamed = {"value": False}

            async def on_delta(delta: str) -> None:
                streamed["value"] = True
                await emit(TextDelta(delta=delta))

            response = await self._router.generate(
                GenerateRequest(messages=messages, tools=self._tools.definitions()),
                on_delta=on_delta,
            )

            # Emit the model's reasoning/thinking if it produced any.
            if response.reasoning:
                await emit(Thinking(text=response.reasoning))

            if not response.wants_tools:
                # Non-streaming providers return the full text without deltas;
                # emit it once so the client still renders a complete answer.
                if response.text and not streamed["value"]:
                    await emit(TextDelta(delta=response.text))
                await emit(Done(text=response.text or ""))
                return

            for call in response.tool_calls:
                await emit(ToolCallEvent(name=call.name, arguments=call.arguments))

                started = time.monotonic()
                result = await self._tools.execute(call, self._ctx)
                duration = round(time.monotonic() - started, 2)
                await emit(
                    ToolResultEvent(
                        name=call.name,
                        ok=result.ok,
                        summary=result.summary,
                        duration_seconds=duration,
                        detail=result.detail,
                    )
                )

                messages.append(
                    Message(role="assistant", content=None, tool_calls=[call])
                )
                messages.append(
                    Message(
                        role="tool",
                        content=result.content,
                        tool_call_id=call.id,
                        name=call.name,
                    )
                )

        await emit(Error(message=f"stopped after {self._max_iterations} iterations"))
