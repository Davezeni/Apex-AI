"""FastAPI application: health, chat (HTTP + WebSocket), conversations,
workspace, and knowledge endpoints.

Layer 1 wires the full tool set (filesystem, sandbox, GitHub, knowledge,
document conversion, web search) behind the agent loop. Live inference and
sandbox/GitHub calls require a configured environment (keys, Docker, token).
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent.core import Agent
from .agent.events import Done, Error
from .config import ROOT_DIR, load_settings
from .container import (
    build_adapters,
    build_github,
    build_knowledge,
    build_router,
    build_sandbox,
    build_store,
    build_tool_context,
    build_tools,
)

from .router.schema import Message
from .workspace.protect import WorkspaceProtection

settings = load_settings()
adapters = build_adapters(settings)
router = build_router(settings, adapters)
store = build_store(settings)
knowledge = build_knowledge(settings)
github = build_github(settings)
sandbox = build_sandbox(settings)
tools = build_tools(settings)
ctx = build_tool_context(settings, github=github, sandbox=sandbox, knowledge=knowledge)
agent = Agent(router, tools, ctx, max_iterations=settings.max_iterations)

# Workspace protection: keep the workspace lean by excluding artifacts.
protection = WorkspaceProtection(settings.workspace_root)
protection.ensure_defaults()

app = FastAPI(title="Apex AI", version="0.3.0")

# Preview state: tracks how the built app is being previewed.
#   mode: "none" | "static" (serve workspace files, works anywhere) | "server"
#         (proxy to a dev server running in the sandbox).
_preview_state: dict = {"mode": "none", "port": None, "url": None}


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    events: list[dict]
    answer: str


class ConversationCreate(BaseModel):
    title: str = "New conversation"


def _event_to_dict(event) -> dict:
    data = {"type": event.__class__.__name__}
    data.update({f: getattr(event, f) for f in event.__dataclass_fields__})
    return data


def _history_for(cid: str, limit: int = 20) -> list[Message]:
    """Rebuild a model-ready history from a conversation's persisted messages.

    Only plain user/assistant text is included (tool internals are skipped),
    so the model gets clean conversational context without its own tool
    plumbing bloating the prompt.
    """
    history: list[Message] = []
    for m in store.list_messages(cid)[-limit:]:
        if m["role"] in ("user", "assistant") and m["kind"] == "text" and m["content"].strip():
            history.append(Message(role=m["role"], content=m["content"]))
    return history


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "providers": list(adapters),
        "pool": [e.model for e in router._pool],  # noqa: SLF001
        "github": github is not None,
        "sandbox": sandbox is not None,
    }


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #

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
            if not isinstance(message, str) or not message.strip():
                continue

            # Persistent memory: load the conversation's history, then save the
            # user + assistant turns so the model remembers context across turns.
            cid = data.get("conversation_id")
            history = _history_for(cid) if cid else None

            if cid:
                store.add_message(cid, "user", message)

            answer: list[str] = []

            async def emit2(event) -> None:
                await emit(event)
                if isinstance(event, Done):
                    answer.append(event.text)

            await agent.run(message, history=history, emit=emit2)

            if cid:
                store.add_message(cid, "assistant", "".join(answer))
    except WebSocketDisconnect:
        pass


# --------------------------------------------------------------------------- #
# Conversations (persistence)
# --------------------------------------------------------------------------- #

@app.get("/api/conversations")
async def list_conversations() -> list[dict]:
    return store.list_conversations()


@app.post("/api/conversations")
async def create_conversation(req: ConversationCreate) -> dict:
    return store.create_conversation(req.title)


@app.get("/api/conversations/{cid}")
async def get_conversation(cid: str) -> dict:
    conv = store.get_conversation(cid)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    conv["messages"] = store.list_messages(cid)
    return conv


@app.delete("/api/conversations/{cid}")
async def delete_conversation(cid: str) -> dict:
    store.delete_conversation(cid)
    return {"ok": True}


@app.post("/api/conversations/{cid}/messages")
async def add_message(cid: str, req: ChatRequest) -> dict:
    if store.get_conversation(cid) is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    store.add_message(cid, "user", req.message)
    # Run the agent and persist the assistant reply (text messages only).
    answer_parts: list[str] = []

    async def emit(event) -> None:
        if isinstance(event, Done):
            answer_parts.append(event.text)

    await agent.run(req.message, emit=emit)
    answer = "".join(answer_parts)
    store.add_message(cid, "assistant", answer)
    return {"answer": answer}


# --------------------------------------------------------------------------- #
# Workspace (file tree + export)
# --------------------------------------------------------------------------- #

@app.get("/api/workspace/tree")
async def workspace_tree(all: bool = False) -> list[str]:
    root = settings.workspace_root
    if not root.exists():
        return []
    entries = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if not all and protection.excluded(rel):
            continue
        entries.append(str(rel))
    return entries


@app.get("/api/workspace/protection")
async def workspace_protection() -> dict:
    report = protection.scan()
    report["included_human"] = WorkspaceProtection.human(report["included_bytes"])
    report["excluded_human"] = WorkspaceProtection.human(report["excluded_bytes"])
    return report


@app.get("/api/workspace/file")
async def workspace_file(path: str) -> dict:
    target = (settings.workspace_root / path).resolve()
    if not target.is_relative_to(settings.workspace_root.resolve()):
        raise HTTPException(status_code=400, detail="path escapes workspace")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return {"path": path, "content": target.read_text(encoding="utf-8", errors="replace")}


@app.get("/api/workspace/export")
async def workspace_export() -> FileResponse:
    tmp = Path(tempfile.mkdtemp()) / "workspace.zip"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in settings.workspace_root.rglob("*"):
            if p.is_file():
                rel = p.relative_to(settings.workspace_root)
                if protection.excluded(rel):
                    continue  # skip dependency/build artifacts
                zf.write(p, rel)
    return FileResponse(tmp, media_type="application/zip", filename="workspace.zip")


@app.post("/api/workspace/upload")
async def workspace_upload(file: UploadFile) -> dict:
    data = await file.read()
    target = settings.workspace_root / Path(file.filename or "upload").name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"path": str(target.relative_to(settings.workspace_root))}


# --------------------------------------------------------------------------- #
# Knowledge
# --------------------------------------------------------------------------- #

class KnowledgeAdd(BaseModel):
    source: str
    text: str


@app.post("/api/knowledge")
async def knowledge_add(req: KnowledgeAdd) -> dict:
    import uuid

    n = await knowledge.add(str(uuid.uuid4()), req.source, req.text)
    return {"chunks": n}


# --------------------------------------------------------------------------- #
# Preview — serve/proxy the app the agent built.
# --------------------------------------------------------------------------- #

class PreviewStart(BaseModel):
    command: str = ""
    port: int = 0
    mode: str = "static"  # "static" (no sandbox needed) | "server" (sandbox)


@app.get("/api/preview")
async def preview_status() -> dict:
    base = "/preview"
    return {
        "mode": _preview_state["mode"],
        "url": f"{base}/" if _preview_state["mode"] != "none" else None,
        "port": _preview_state["port"],
    }


@app.post("/api/preview/start")
async def preview_start(req: PreviewStart) -> dict:
    """Point the preview at either the workspace's static files or a running
    dev server (sandbox required for 'server' mode)."""
    if req.mode == "server":
        if sandbox is None or not await sandbox.available():
            raise HTTPException(status_code=400, detail="sandbox not available (preview needs Docker/Codespaces)")
        if not req.command or not req.port:
            raise HTTPException(status_code=400, detail="server mode requires command and port")
        await sandbox.run_server(req.command, req.port)
        url = await sandbox.server_url(req.port)
        _preview_state.update(mode="server", port=req.port, url=url)
        return {"mode": "server", "url": "/preview/", "port": req.port}

    # Static: serve workspace files directly (works everywhere, incl. Render).
    _preview_state.update(mode="static", port=None, url=None)
    return {"mode": "static", "url": "/preview/"}


async def _proxy(port: int, path: str, request: Request) -> Response:
    """Reverse-proxy a request to the sandbox dev server."""
    target = await sandbox.server_url(port)
    url = f"{target}/{path}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        upstream = await client.request(
            request.method,
            url,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")},
            content=await request.body(),
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={"Content-Type": upstream.headers.get("content-type", "text/html")},
    )


@app.api_route("/preview/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def preview(path: str, request: Request):
    mode = _preview_state["mode"]

    if mode == "server":
        if sandbox is None:
            raise HTTPException(status_code=400, detail="sandbox not configured")
        return await _proxy(_preview_state["port"], path, request)

    if mode == "static":
        root = settings.workspace_root
        target = (root / path).resolve()
        if path == "" or path.endswith("/"):
            target = (root / (path or "") / "index.html").resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise HTTPException(status_code=404, detail="preview file not found (create an index.html or start a server)")
        return FileResponse(target)

    raise HTTPException(status_code=404, detail="no preview started (create a web app, or call /api/preview/start)")


# --------------------------------------------------------------------------- #
# Static frontend (SPA) — served when built, so ONE service hosts everything.
# This is what enables single-origin deployment (Render/VM): the frontend's
# relative /api and /ws URLs hit this same server with no CORS/proxy config.
# --------------------------------------------------------------------------- #

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_relative_to(FRONTEND_DIST.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
