# Apex AI — Software Design Document (SDD)

**Document ID:** AX-DESIGN-001
**Version:** 1.1
**Date:** 2026-08-13

This document provides the **detailed low-level design**: module structure, key interfaces, data models, API surface, and algorithms. It refines the architecture in [02-system-architecture.md](02-system-architecture.md).

---

## 1. Repository Layout

```
apex-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, routes, WS endpoints
│   │   ├── config.py               # settings loader (env + config.yaml)
│   │   ├── agent/
│   │   │   ├── core.py             # the agent loop
│   │   │   ├── registry.py         # agent registry (multi-agent-ready)
│   │   │   ├── types.py            # AgentEvent, Step, etc.
│   │   ├── router/
│   │   │   ├── router.py           # pool, round-robin, cooldown
│   │   │   ├── schema.py           # common request/response model
│   │   │   └── providers/
│   │   │       ├── base.py         # ProviderAdapter interface
│   │   │       ├── groq.py
│   │   │       ├── gemini.py
│   │   │       └── ollama.py
│   │   ├── tools/
│   │   │   ├── base.py             # Tool base + decorator
│   │   │   ├── registry.py         # ToolRegistry
│   │   │   ├── filesystem.py
│   │   │   ├── web_search.py
│   │   │   ├── github.py
│   │   │   ├── knowledge.py
│   │   │   ├── ask_user.py
│   │   │   └── sandbox.py
│   │   ├── sandbox/
│   │   │   ├── base.py             # Sandbox interface
│   │   │   ├── codespaces.py       # GitHub Codespaces backend
│   │   │   └── docker.py           # local Docker backend
│   │   ├── memory/
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   ├── store.py            # conversation store
│   │   │   └── rag.py              # ChromaDB + embeddings
│   │   ├── media/                  # document & media pipeline
│   │   │   ├── ingest.py           # parse docx/xlsx/pptx/pdf/csv/img/zip
│   │   │   ├── vision.py           # describe_image, ocr_image
│   │   │   ├── image_gen.py        # generate_image, edit_image
│   │   │   ├── convert.py          # format conversion (md interchange)
│   │   │   ├── charts.py           # matplotlib/plotly
│   │   │   └── author.py           # docs, decks, citations, links
│   │   └── health/
│   │       └── watchdog.py         # monitoring + self-heal
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/             # Chat, Sidebar, CodeSpace, Preview, Question…
│   │   ├── stores/                 # Zustand stores
│   │   ├── lib/ws.ts               # WebSocket client
│   │   ├── lib/api.ts              # REST client
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── config.example.yaml
└── README.md
```

---

## 2. Agent Core Design

### 2.1 The Loop (pseudocode → real interface)

```python
class Agent:
    def __init__(self, router: ModelRouter, tools: ToolRegistry, store: MemoryStore):
        ...

    async def run_turn(self, conversation_id: str, user_msg: str,
                       emit: EventEmitter) -> str:
        messages = self.store.load_messages(conversation_id)
        messages.append(role="user", content=user_msg)

        for _ in range(self.max_iterations):
            if self.cancelled(conversation_id):
                break

            response = await self.router.generate(
                messages=messages,
                tools=self.tools.schemas(),
                on_text=emit.text_delta,          # stream
            )

            if response.tool_calls:
                emit.thinking(response.thought)    # optional reasoning
                for call in response.tool_calls:
                    emit.tool_call(call)
                    result = await self.tools.execute(call)
                    emit.tool_result(call.id, result)
                    messages.append(assistant_tool_calls=call)
                    messages.append(tool_result=result)
                continue                            # loop again

            emit.done()
            self.store.save_messages(conversation_id, messages)
            return response.text

        return "Stopped: iteration limit reached."
```

### 2.2 Event Stream (WebSocket protocol)

The backend emits JSON events; the frontend renders each type differently.

| Event | Payload | UI rendering |
|-------|---------|--------------|
| `text_delta` | `{ delta }` | append to streaming bubble |
| `thinking` | `{ text, step }` | collapsible "Thinking" card |
| `tool_call` | `{ id, name, args }` | card: "🔧 Running `write_file`" |
| `tool_result` | `{ id, ok, summary, detail }` | expandable result body |
| `question` | `{ id, prompt, options[] }` | in-chat choice UI |
| `done` | `{ final }` | close stream |
| `error` | `{ message }` | error toast |

### 2.3 Cancellation
A `conversation_id → threading.Event` map; `POST /chat/{id}/cancel` sets the event; the loop checks it each iteration and between tool calls.

---

## 3. Model Router Design

### 3.1 Common schema (normalization target)

```python
@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict            # JSON Schema

@dataclass
class GenerateRequest:
    messages: list[Message]     # normalized {role, content, tool_calls, tool_call_id}
    tools: list[ToolDef]
    max_tokens: int

@dataclass
class GenerateResponse:
    text: str | None
    tool_calls: list[ToolCall]  # {id, name, arguments}
```

### 3.2 Provider adapter interface

```python
class ProviderAdapter(ABC):
    name: str
    async def generate(self, req: GenerateRequest) -> GenerateResponse: ...
    def supports_tool_calls(self) -> bool: ...
```

Each adapter maps the normalized schema to its provider's SDK/HTTP API and back. Providers without native tool calling get tools injected as a JSON prompt convention and parsed from the response.

> **Gemini auth-key note (June 2026):** Google has migrated Gemini keys from `AIza...` "Traffic keys" to `AQ.Ab...` "Authentication keys." The `AQ.` key works on the **native** endpoint (`generativelanguage.googleapis.com`) and with the official `google-genai` SDK, but is **rejected (401) on OpenAI-compatible endpoints** and by tools that hardcode the `AIza` regex. Therefore the Gemini adapter MUST use the native `google-genai` SDK / native REST, not an OpenAI-compatible shim. (Standard `AIza` keys are being phased out: unrestricted keys rejected after June 19, 2026; all standard keys retired ~September 2026.)

### 3.3 Pool, round-robin, failover, cooldown

```python
@dataclass
class PoolEntry:
    provider: str          # "groq" | "gemini" | "ollama"
    model: str             # e.g. "llama-3.3-70b-versatile"
    priority: int          # lower = preferred
    cooldown_until: float = 0.0   # unix time

class ModelRouter:
    def __init__(self, pool: list[PoolEntry], adapters: dict[str, ProviderAdapter]):
        ...

    async def generate(self, req) -> GenerateResponse:
        ordered = sorted(self._available(), key=lambda e: (e.priority, e.model))
        errors = []
        for _ in range(len(ordered) * 2):            # wrap-around
            entry = ordered[self._cursor % len(ordered)]
            self._cursor += 1
            try:
                return await self.adapters[entry.provider].generate(req)
            except RateLimitError as e:
                entry.cooldown_until = now() + self.cooldown_seconds
                errors.append(str(e))
                continue
        raise AllModelsExhausted(errors)
```

**Behaviors:**
- `_available()` filters out entries still within cooldown.
- Local Ollama (priority = lowest) is always available → the pool never hard-fails if Ollama is running.
- Round-robin cursor spreads load; failover handles rate limits; cooldown avoids retrying throttled models for a window.

### 3.4 Configuration (`config.example.yaml`)

```yaml
models:
  pool:
    - { provider: groq,   model: "llama-3.3-70b-versatile", priority: 1 }
    - { provider: gemini, model: "gemini-2.0-flash",        priority: 2 }
    - { provider: groq,   model: "qwen-2.5-32b",            priority: 3 }
    - { provider: ollama, model: "qwen2.5:14b",             priority: 9 }  # fallback
  cooldown_seconds: 60
  max_iterations: 12
  keys:
    groq_api_key: ${GROQ_API_KEY}      # optional
    gemini_api_key: ${GEMINI_API_KEY}  # optional
```

> **Note:** exact model IDs are configurable because providers update their catalogs; the IDs above are current examples to be verified at build time.

---

## 4. Tool Registry Design

### 4.1 Tool interface

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict                # JSON Schema

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult: ...
```

`ToolContext` carries the workspace path, sandbox handle, authenticated clients (GitHub), and the event emitter.

### 4.2 Registration (decorator-based, zero core changes)

```python
@tool("write_file", "Create or overwrite a file in the workspace", {
    "path": {"type": "string"},
    "content": {"type": "string"},
})
async def write_file(args, ctx):
    safe = resolve_within(args["path"], ctx.workspace_root)  # traversal guard
    safe.write_text(args["content"])
    return ToolResult(ok=True, summary=f"Wrote {args['path']}")
```

### 4.3 Filesystem safety (path-traversal protection)

```python
def resolve_within(path: str, root: Path) -> Path:
    p = (root / path).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ToolError("Path escapes workspace root")
    return p
```

### 4.4 Document & Media Tools (the `media/` pipeline)

All non-code capabilities share one design: **parse → markdown interchange → emit**.

```python
# ingestion
async def parse_document(path: Path) -> ParsedDoc:      # {text, tables, metadata}
    ext = path.suffix.lower()
    return PARSERS[ext](path)                           # pdf→pdfplumber, xlsx→openpyxl, ...

# conversion (md is the hub)
async def convert_file(src: Path, dst_fmt: str) -> Path:
    md = to_markdown(src)                               # parser
    return WRITERS[dst_fmt](md)                         # .docx/.xlsx/.pdf/.pptx/.md/.html

# vision
async def describe_image(path: Path) -> str:            # local VLM or Gemini vision
async def ocr_image(path: Path) -> str:                 # Tesseract / VLM

# image generation
async def generate_image(prompt: str) -> Path:          # Pollinations.ai / ComfyUI

# charts
async def generate_chart(data: DataFrame, kind: str) -> Path:
    # matplotlib → PNG/SVG, or plotly → interactive HTML

# authoring
async def generate_document(template: str, ctx: dict) -> Path:
    # Jinja2 markdown template → .md/.docx/.pptx/.pdf
```

**Conversion matrix (parser → writer):**

| From \ To | md | docx | xlsx | pdf | pptx | html |
|-----------|----|------|------|-----|------|------|
| csv/txt/md/html | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| xlsx | ✓ | ✓ | — | ✓ | — | ✓ |
| docx | ✓ | — | — | ✓ | — | ✓ |
| pdf | ✓ (extract) | ✓ | ✓ (tables) | — | — | — |
| pptx | ✓ (extract) | — | — | — | — | — |

**Library map (all free/open source):**

| Format | Read | Write |
|--------|------|-------|
| CSV / tabular | pandas | pandas |
| XLSX | openpyxl / pandas | openpyxl / pandas |
| DOCX | python-docx | python-docx |
| PPTX | python-pptx | python-pptx |
| PDF | pdfplumber / PyMuPDF | reportlab / weasyprint |
| Images (OCR) | Tesseract / VLM | — |
| Images (gen) | — | Pollinations.ai / ComfyUI |
| Charts | — | matplotlib / Plotly |

**Citations & links:** `cite_source` returns a structured citation `{quote, source_url, source_title, retrieved_at}`; the authoring layer renders it as a Markdown blockquote with an external link. `generate_document` auto-generates internal anchor links from headings (Table of Contents).

### 4.5 `ask_user` (in-chat questions)

Special tool: `execute()` returns a `ToolResult` whose payload is a `Question`. The agent loop detects this and **pauses**, emitting a `question` event; the turn resumes when the user answers (answer appended as the tool result). This is how "choice questions" surface in-chat.

---

## 5. Data Models (SQLite / SQLAlchemy)

```python
class Conversation(Base):
    id: str            # uuid
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message]

class Message(Base):
    id: str
    conversation_id: str
    role: str          # user | assistant | tool
    content: str       # text, or JSON for tool_calls/results
    kind: str          # text | tool_call | tool_result | question | answer
    created_at: datetime

class ToolLog(Base):
    id: str
    conversation_id: str
    tool_name: str
    args_json: str
    ok: bool
    summary: str
    created_at: datetime
```

The vector store (ChromaDB) holds `(document_id, chunk_text, embedding)` with metadata `{source, chunk_index}`.

---

## 6. API Surface

### 6.1 REST

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | liveness/readiness |
| GET | `/api/conversations` | list conversations |
| POST | `/api/conversations` | create; body `{title?}` |
| GET | `/api/conversations/{id}` | messages + metadata |
| DELETE | `/api/conversations/{id}` | delete |
| POST | `/api/chat/{id}/cancel` | cancel running turn |
| GET | `/api/workspace/tree` | file tree |
| GET | `/api/workspace/file?path=` | read file |
| POST | `/api/workspace/export` | zip download |
| POST | `/api/workspace/upload` | upload file(s) (multipart) |
| POST | `/api/files/parse` | parse uploaded doc → text + tables |
| POST | `/api/files/convert?to=` | convert file format |
| POST | `/api/media/describe-image` | vision description |
| POST | `/api/media/ocr` | OCR text extraction |
| POST | `/api/media/generate-image` | text-to-image |
| POST | `/api/media/chart` | generate chart |
| POST | `/api/docs/generate` | generate SAD/SDD/PRD/README/deck |
| GET | `/api/knowledge` | list docs |
| POST | `/api/knowledge` | add doc (multipart) |
| POST | `/api/github/connect` | store PAT (scopes validated) |
| GET | `/api/github/repos` | list repos |

### 6.2 WebSocket

| Path | Purpose |
|------|---------|
| `/ws/chat/{conversation_id}` | stream agent events for a turn; client sends `{type:"user", content}` |

### 6.3 Preview proxy

```
GET /preview/*  →  proxy to sandbox dev server (Codespace port or Docker container port)
```
The frontend iframe uses this relative path, so browser code never touches `localhost` or a sandbox IP directly.

---

## 7. Sandbox Design

### 7.1 Interface

```python
class Sandbox(ABC):
    async def start(self, workspace: Path) -> SandboxHandle
    async def run_command(self, cmd: str) -> CommandResult   # {exit_code, stdout, stderr}
    async def expose_port(self, port: int) -> str            # returns preview URL
    async def stop(self)
```

### 7.2 GitHub Codespaces backend
- Workspace is tied to a repo (created/cloned via the GitHub tool).
- `run_command` uses the Codespaces API / `gh codespace` CLI to execute in the Codespace.
- `expose_port` maps the Codespace forwarded port to the preview proxy.

### 7.3 Docker backend (fallback)
- A container image with common runtimes (Node, Python) mounts the workspace.
- `run_command` = `docker exec`; `expose_port` = publish + proxy.
- On the free VM, this runs Docker-in-Docker or a sibling container.

---

## 8. Web Search Design

- Default: **DuckDuckGo** (no key) via `ddgs` library or scraping the HTML endpoint.
- Optional: **Tavily** (keyed) for higher-quality structured results.
- Tool returns `[{title, url, snippet}]`, capped at N results, injected as context.

---

## 9. Health / Watchdog Design

```python
class Watchdog:
    async def loop(self):                      # background task
        while True:
            metrics = self.collect()           # cpu, mem, disk, error_rate
            if metrics.anomalous():
                log.alert(metrics)
            for svc in self.subcomponents():
                if not svc.healthy():
                    self.restart(svc)          # e.g. restart sandbox / ollama
            await asyncio.sleep(self.interval)
```

- `/health/live` (process up) vs `/health/ready` (deps reachable: DB, sandbox, ≥1 model source).
- Self-heal is **restart + revert-to-last-good-commit** for sandbox/workspace; the platform's own code is not self-modified in Layer 1.

---

## 10. Security Design (enforcement points)

| Threat | Control |
|--------|---------|
| Malicious generated code | Sandbox isolation (Codespaces/Docker), no host execution |
| Path traversal | `resolve_within` guard on every FS tool |
| Secret leakage | Keys only from env; redaction in logs; git-ignored `.env` |
| Unauthorized GitHub actions | Least-privilege PAT scopes; first-use confirmation |
| Prompt injection via search results | Results treated as untrusted data, passed as context not instructions |
| Remote exposure | UI binds localhost by default; reverse proxy is opt-in |

---

## 11. Testing Strategy (summary)

| Layer | Approach |
|-------|----------|
| Unit | Router failover logic; FS traversal guard; schema normalization (mocked providers) |
| Integration | Tool registry end-to-end with a fake sandbox; SQLite persistence |
| E2E | Chat → write files → run → preview, against a Docker sandbox |
| Contract | WebSocket event schema; provider adapter fixtures |

---

## 12. Open Design Decisions (to resolve during build)

1. Exact free-tier model IDs (verify at build time against Groq/Gemini catalogs).
2. Codespaces CLI (`gh`) vs API for `run_command` — CLI is simpler to start.
3. Embedding model default (BGE-small local vs Ollama embeddings) — decide by footprint on target host.
4. Whether Layer 1 ships GitHub OAuth or PAT-only (PAT-only is simpler; OAuth later).
