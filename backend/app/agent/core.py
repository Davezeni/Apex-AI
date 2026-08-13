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
    "You are Apex AI, a senior software engineering assistant embedded in a "
    "self-hosted builder. You create files, scaffold project structures, run "
    "commands, search the web, and generate documents, images, and charts to "
    "complete the user's goals.\n\n"
    "Working style:\n"
    "- Think through the task step by step before acting: understand the goal, "
    "plan the approach, then execute.\n"
    "- Use your tools whenever they genuinely help (files, sandbox, search, "
    "vision, charts, documents).\n"
    "- Be concise but complete: after acting, briefly state what you did and why.\n"
    "- When you finish, end with a short summary covering: (1) what was DONE, "
    "(2) what is NOT yet done or needs attention, and (3) one or two concrete "
    "next-step recommendations.\n"
    "- Be honest: flag anything you could not verify (untested code, missing "
    "credentials, unavailable sandbox) instead of implying it works."
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
