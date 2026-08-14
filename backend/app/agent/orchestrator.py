"""Orchestrator: classify → run specialist → (optionally) review.

The multi-agent coordinator. For each turn it:
1. classifies the task and picks the right specialist,
2. runs that specialist agent (with its persona, tool subset, and model bias),
3. for technical tasks, runs a separate REVIEWER agent (a different, strong
   model) to critique the work — quality above any single model.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..router.router import ModelRouter
from ..router.schema import GenerateRequest, Message
from ..tools.registry import ToolContext, ToolRegistry
from .core import Agent
from .events import AgentEvent, Review, Summary
from .specialists import REVIEWER, SUMMARY_PERSONA, classify_and_pick
from .tasks import TaskKind, classify

Emit = Callable[[AgentEvent], Awaitable[None]]

# Tasks that get a review pass (technical work benefits from critique).
_REVIEWED_KINDS = {TaskKind.CODE, TaskKind.MATH, TaskKind.DESIGN, TaskKind.DATA}


class Orchestrator:
    """Runs the specialist agent and, for technical tasks, a reviewer."""

    def __init__(
        self,
        router: ModelRouter,
        tools: ToolRegistry,
        ctx: ToolContext,
        *,
        max_iterations: int = 12,
        review: bool = True,
    ) -> None:
        self._router = router
        self._tools = tools
        self._ctx = ctx
        self._max_iterations = max_iterations
        self._review = review

    async def run(
        self,
        user_message: str,
        history: list[Message] | None = None,
        emit: Emit | None = None,
    ) -> str:
        async def noop(event: AgentEvent) -> None:
            del event

        emit = emit or noop

        kind = classify(user_message).kind
        specialist = classify_and_pick(user_message)

        # 1. Run the specialist.
        agent = Agent(
            self._router, self._tools, self._ctx,
            max_iterations=self._max_iterations,
        )
        answer = await agent.run(user_message, history=history, emit=emit, specialist=specialist)

        # 2. Review technical work with a separate, strong model.
        if self._review and kind in _REVIEWED_KINDS and answer.strip():
            review_text = await self._review_work(user_message, answer)
            if review_text:
                await emit(Review(text=review_text))

        # 3. Emit a final summary of what was done (best-effort).
        if answer.strip():
            summary_text = await self._summarize(user_message, answer)
            if summary_text:
                await emit(Summary(text=summary_text))

        return answer

    async def _review_work(self, request: str, answer: str) -> str:
        """Run the reviewer on the specialist's output (a different model).

        Never raises — if the reviewer cannot run (rate limits, no models),
        we skip the review and keep the specialist's answer.
        """
        try:
            prompt = REVIEWER.persona.format(work=answer, request=request)
            result = await self._router.generate(
                GenerateRequest(messages=[Message(role="system", content=prompt)], tools=[]),
                prefer_models=REVIEWER.preferred_models or None,
            )
            return (result.text or "").strip()
        except Exception:  # noqa: BLE001 — review is best-effort
            return ""

    async def _summarize(self, request: str, answer: str) -> str:
        """Produce a final done/not-done/next-steps summary (best-effort)."""
        try:
            prompt = SUMMARY_PERSONA.format(request=request, work=answer)
            result = await self._router.generate(
                GenerateRequest(messages=[Message(role="system", content=prompt)], tools=[]),
                prefer_models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
            )
            return (result.text or "").strip()
        except Exception:  # noqa: BLE001 — summary is best-effort
            return ""


__all__ = ["Orchestrator"]
