"""FastAPI application: health, HTTP chat, and WebSocket streaming endpoints.

- `/health`        — liveness/readiness + which providers are configured.
- `/api/chat`      — one stateless turn, returns the full event list (JSON).
- `/ws/chat`       — streaming turn(s) over WebSocket; the agent emits events
                     (text deltas, tool calls/results, done/error) live.

Conversation persistence (memory layer) is a later increment; both endpoints
are currently stateless per turn.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .agent.core import Agent
from .agent.events import Done, Error
from .config import load_settings
from .container import (
    build_adapters,
    build_router,
    build_tool_context,
    build_tools,
)

settings = load_settings()
adapters = build_adapters(settings)
router = build_router(settings, adapters)
tools = build_tools(settings)
ctx = build_tool_context(settings)
agent = Agent(router, tools, ctx, max_iterations=settings.max_iterations)

app = FastAPI(title="Apex AI", version="0.2.0")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    events: list[dict]
    answer: str


def _event_to_dict(event) -> dict:
    data = {"type": event.__class__.__name__}
    data.update({f: getattr(event, f) for f in event.__dataclass_fields__})
    return data


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "providers": list(adapters),
        "pool": [e.model for e in router._pool],  # noqa: SLF001
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    events: list[dict] = []
    answer = ""

    async def emit(event) -> None:
        nonlocal answer
        if isinstance(event, Error):
            raise HTTPException(status_code=502, detail=event.message)
        if isinstance(event, Done):
            answer = event.text
        events.append(_event_to_dict(event))

    await agent.run(req.message, emit=emit)
    return ChatResponse(events=events, answer=answer)


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    await ws.accept()

    async def emit(event) -> None:
        await ws.send_json(_event_to_dict(event))

    try:
        while True:
            data = await ws.receive_json()
            message = data.get("message")
            if isinstance(message, str) and message.strip():
                await agent.run(message, emit=emit)
    except WebSocketDisconnect:
        pass
