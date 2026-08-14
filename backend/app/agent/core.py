"""The agent loop: reason → act → observe → repeat.

A single loop that can run as any specialist (via a Specialist config) — the
persona, tool subset, and preferred models are all parameterized. RAG
auto-retrieval grounds answers in the user's knowledge base before the first
model call. Structured so an orchestrator can run multiple specialists.
"""

from __future__ import annotations

import logging
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
from .specialists import Specialist, classify_and_pick

logger = logging.getLogger("apex.agent")

Emit = Callable[[AgentEvent], Awaitable[None]]

DEFAULT_SYSTEM_PROMPT = (
    "You are Apex AI, a capable assistant embedded in a self-hosted builder. "
    "Work step by step, use tools when they help, and be honest about what "
    "you did and could not verify."
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
        auto_rag: bool = True,
    ) -> None:
        self._router = router
        self._tools = tools
        self._ctx = ctx
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations
        self._auto_rag = auto_rag

    async def _retrieve_knowledge(self, user_message: str) -> str | None:
        """Auto-retrieve relevant chunks from the knowledge base, if any."""
        if not self._auto_rag:
            return None
        kb = self._ctx.knowledge
        if kb is None:
            return None
        try:
            chunks = await kb.query(user_message, top_k=3)
        except Exception:  # noqa: BLE001
            return None
        if not chunks:
            return None
        lines = ["Relevant knowledge from the user's documents (use this to ground your answer):"]
        for c in chunks:
            lines.append(f"[{c.source}] {c.text}")
        return "\n\n".join(lines)

    def _workspace_context(self) -> str | None:
        """Build a compact snapshot of the current workspace file tree so the
        agent 'sees' what it has already built and can maintain continuity
        when the user asks to adjust/extend earlier work.

        Kept small (<= 40 files, short) so it doesn't blow past small models'
        token limits (which caused HTTP 413 'request too large')."""
        root = self._ctx.workspace_root
        try:
            entries = sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())
        except Exception:  # noqa: BLE001
            return None
        if not entries:
            return None
        names = [str(e) for e in entries][:40]
        lines = [
            "Current workspace files (built earlier — read_file to inspect, "
            "write_file/edit_file to adjust):",
        ]
        lines += [f"- {n}" for n in names]
        if len(entries) > 40:
            lines.append(f"... and {len(entries) - 40} more")
        return "\n".join(lines)

    async def run(
        self,
        user_message: str,
        history: list[Message] | None = None,
        emit: Emit | None = None,
        specialist: Specialist | None = None,
    ) -> str:
        """Run one turn as the given specialist (or auto-classified).

        Returns the final answer text.
        """
        emit = emit or _noop
        specialist = specialist or classify_and_pick(user_message)

        # Grounding: retrieve relevant knowledge before the first call.
        knowledge = await self._retrieve_knowledge(user_message)
        workspace = self._workspace_context()

        messages: list[Message] = [Message(role="system", content=specialist.persona)]
        if knowledge:
            messages.append(Message(role="system", content=knowledge))
        if workspace:
            messages.append(Message(role="system", content=workspace))
        messages += list(history or [])
        messages.append(Message(role="user", content=user_message))

        tool_defs = self._tools.definitions(specialist.tool_filter)

        final_text = ""
        streamed_parts: list[str] = []  # accumulate streamed text across turns

        for _ in range(self._max_iterations):
            streamed = {"value": False}

            async def on_delta(delta: str) -> None:
                streamed["value"] = True
                streamed_parts.append(delta)
                await emit(TextDelta(delta=delta))

            try:
                response = await self._router.generate(
                    GenerateRequest(messages=messages, tools=tool_defs),
                    on_delta=on_delta,
                    prefer_models=specialist.preferred_models or None,
                )
            except Exception as exc:  # noqa: BLE001 — log full error, show clean message
                logger.warning("model generation failed: %s", exc)
                await emit(
                    Error(
                        message=(
                            "All models are temporarily busy or rate-limited. "
                            "Please wait a few seconds and try again."
                        )
                    )
                )
                return final_text

            if response.reasoning:
                await emit(Thinking(text=response.reasoning))

            if not response.wants_tools:
                if response.text and not streamed["value"]:
                    await emit(TextDelta(delta=response.text))
                # Prefer the final content; fall back to streamed text, then
                # to reasoning (some reasoning models put the answer there).
                final_text = (
                    response.text
                    or "".join(streamed_parts).strip()
                    or response.reasoning
                    or ""
                )
                await emit(Done(text=final_text))
                return final_text

            for call in response.tool_calls:
                # Guard: never execute a tool outside this specialist's set.
                if specialist.tool_filter is not None and call.name not in specialist.tool_filter:
                    await emit(
                        ToolResultEvent(
                            name=call.name, ok=False,
                            summary=f"tool not allowed for {specialist.name}",
                            duration_seconds=0.0, detail={},
                        )
                    )
                    messages.append(Message(role="assistant", content=None, tool_calls=[call]))
                    messages.append(Message(role="tool", content="tool not allowed for this specialist", tool_call_id=call.id, name=call.name))
                    continue

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

                messages.append(Message(role="assistant", content=None, tool_calls=[call]))
                messages.append(
                    Message(role="tool", content=result.content, tool_call_id=call.id, name=call.name)
                )

        await emit(Error(message=f"stopped after {self._max_iterations} iterations"))
        return final_text
