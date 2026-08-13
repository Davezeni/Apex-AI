# Apex AI — System Architecture Document (SAD)

**Document ID:** AX-ARCH-001
**Version:** 1.1
**Date:** 2026-08-13

---

## 1. Introduction

This document describes the high-level architecture of **Apex AI**, a free, open-source, self-hosted AI agent platform. It defines the major components, their responsibilities, their interactions, and the technology choices that satisfy the requirements in [01-requirements.md](01-requirements.md).

### 1.1 Architectural Goals
1. **Built on free & open-source, permissively-licensed components** at every layer (the product itself is proprietary).
2. **Fast & light** — low latency streaming, small footprint, single-machine deployable.
3. **Modern & extensible** — pluggable tools, pluggable model providers, multi-agent-ready.
4. **Mobile-first & responsive** — designed for phones first, scaling to multi-pane desktop.
5. **Safe** — generated code runs only in an isolated sandbox.

### 1.2 Architectural Style
Apex AI uses a **modular monolith** with **event-driven streaming**:

- A single **backend service** (FastAPI) hosts the agent core, model router, tool registry, memory, and integrations. It is a monolith in deployment but *modular* in code — each subsystem is an isolated module behind a clean interface.
- A **frontend** (React + Vite) communicates over **REST** (for CRUD) and **WebSocket** (for streaming agent events).
- A **sandbox** (GitHub Codespaces, or local Docker) executes generated code outside the host.

We deliberately avoid a microservices split in Layer 1: it would add operational cost without benefit at single-user scale. The module boundaries below are designed so any module *can* later be extracted into its own service.

---

## 2. System Context

```
                         ┌─────────────────────────────┐
                         │        User's Browser        │
                         │   React UI (chat/code/prev)  │
                         └──────────────┬──────────────┘
                                 HTTPS / WS
                                        │
   ┌────────────────────────────────────┼────────────────────────────────────┐
   │                        Apex AI Backend (FastAPI)                      │
   │  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌────────────┐  │
   │  │ Agent    │ │ Model    │ │ Tool       │ │ Memory   │ │ Health /   │  │
   │  │ Core     │ │ Router   │ │ Registry   │ │ + RAG    │ │ Watchdog   │  │
   │  └──────────┘ └──────────┘ └────────────┘ └──────────┘ └────────────┘  │
   └────┬──────────────┬──────────────┬──────────────┬──────────────────────┘
        │              │              │              │
   ┌────▼────┐   ┌─────▼─────┐  ┌─────▼──────┐  ┌────▼───────┐
   │ Groq    │   │ Google    │  │ GitHub     │  │ Sandbox    │
   │ (hosted)│   │ Gemini    │  │ Codespaces │  │ / Docker   │
   └─────────┘   └───────────┘  │ or local   │  └────────────┘
                                │ Docker     │
   ┌─────────┐   ┌───────────┐  └────────────┘
   │ Ollama  │   │ Web search│   (DuckDuckGo / Tavily)
   │ (local) │   └───────────┘
   └─────────┘
```

---

## 3. Component Description

### 3.1 Agent Core
**Responsibility:** Execute the agent loop — the "reason → act → observe → repeat" cycle.

```
while iterations < MAX:
    response = router.generate(messages, tools)     # reason
    if response has tool_calls:                     # act
        for each call: result = tool_registry.execute(call)
        append results to messages                  # observe
    else:
        return response.text                        # final answer
```

- Maintains the message list (conversation state).
- Emits events to the WebSocket stream: `thinking`, `tool_call`, `tool_result`, `text_delta`, `done`, `question`.
- Enforces iteration caps and user cancellation.
- **Multi-agent hook:** the core is itself a single "agent" instance registered in an **Agent Registry**, so orchestrator/specialist agents can later be added and invoked identically.

### 3.2 Model Router
**Responsibility:** Abstract every model provider behind one interface and pick the right model per request.

Key concepts (see also [03-software-design.md](03-software-design.md) §4):

- **Provider adapters** — one class per provider (Groq, Gemini, Ollama), each normalizing to a common request/response schema.
- **Model pool** — an ordered, configurable list of `(provider, model_id, priority)`.
- **Round-robin + failover + cooldown** — spread requests, skip throttled models, wrap indefinitely, end on local Ollama.
- **Tool-calling normalization** — providers that support native tool calls use them; those that don't are given a JSON "function calling" prompt convention.
- **Gemini auth-key constraint** — Gemini's newer `AQ.` auth keys require the **native** Gemini SDK/endpoint (not OpenAI-compatible routes), so the Gemini adapter uses `google-genai`. See SDD §3.2.

### 3.3 Tool Registry
**Responsibility:** A single place where every capability is registered with a name, description, and JSON Schema.

Tools in Layer 1:
| Tool | Purpose |
|------|---------|
| `list_files`, `read_file`, `write_file`, `edit_file`, `delete_file`, `create_structure` | Filesystem |
| `run_command` | Execute a command **inside the sandbox** |
| `web_search` | Web search |
| `git_clone`, `git_commit`, `git_push`, `git_pull`, `github_create_repo` | GitHub |
| `knowledge_add`, `knowledge_query` | RAG memory |
| `ask_user` | In-chat choice questions (pauses the loop) |
| `export_workspace` | Zip download |
| `upload_file`, `extract_archive` | File ingestion (documents, images, zip) |
| `parse_document`, `summarize_file`, `extract_data` | Document understanding |
| `describe_image`, `ocr_image` | Vision & OCR |
| `generate_image`, `edit_image` | Image generation |
| `convert_file` | Format conversion (pdf/xlsx/csv/docx/pptx/md) |
| `analyze_data`, `generate_chart` | Data analysis & visualization |
| `generate_document`, `generate_deck` | Document & presentation authoring |
| `cite_source` | Quotations/citations with tracked sources |

### 3.4 Memory & Knowledge
**Responsibility:** Persist conversations and power RAG.
- **SQLite** — conversations, messages, tool-call logs (durable, zero-config, light).
- **ChromaDB** — vector store for document embeddings.
- **Embeddings** — local model (e.g., `sentence-transformers` BGE-small, or Ollama embeddings) so the knowledge feature costs nothing.

### 3.5 Sandbox Integration
**Responsibility:** Run agent-generated code safely and expose live previews.
- **Primary:** GitHub Codespaces — the workspace maps to a repo; the agent runs commands in the Codespace.
- **Fallback:** local Docker — a container with the workspace mounted, running a dev server.
- The backend **proxies** the sandbox's dev-server port to the browser iframe, so browser code never calls `localhost` directly.

### 3.5b Document & Media Pipeline

A dedicated subsystem for everything "non-code" the agent produces and consumes. It is intentionally isolated from the agent core so it can be scaled or replaced independently.

| Sub-capability | Approach |
|----------------|----------|
| **Ingestion** | Parse docx (python-docx), xlsx (openpyxl/pandas), pptx (python-pptx), pdf (pdfplumber/PyMuPDF), csv/txt/md/html/json (stdlib/pandas); zip via `zipfile`/`shutil` |
| **Vision & OCR** | Local VLM (Ollama `qwen2.5-vl` / `llava`) or free hosted Gemini vision; OCR via Tesseract (optional, local) |
| **Image generation** | Pollinations.ai (free, keyless) or local Stable Diffusion/FLUX (ComfyUI) |
| **Conversion** | pandas + openpyxl (tabular), python-docx (Word), reportlab/weasyprint (PDF), python-pptx (slides), pandoc (multi-format, optional) |
| **Charts** | matplotlib (static PNG/SVG) + Plotly (interactive HTML) |
| **Authoring** | Markdown-first templates → rendered to .md, .docx, .pptx, .html |

The pipeline follows one principle: **markdown is the internal interchange format**; everything else is a target/source format. This keeps every conversion a pair of (parser → md) and (md → writer) steps, so N formats need O(N) adapters instead of O(N²).

### 3.6 Health / Watchdog
**Responsibility:** Liveness/readiness endpoints, resource monitoring, anomaly logging, and self-healing (auto-restart of failed subcomponents). See [03-software-design.md](03-software-design.md) §9.

### 3.7 Frontend
**Responsibility:** The user experience — chat, sidebar, code space, preview, questions.

| Area | Technology | Notes |
|------|-----------|-------|
| Framework | React 18 + TypeScript | Component model, typed |
| Build | Vite | Fast dev server + build |
| Styling | Tailwind CSS | Utility-first, light output |
| Code editor | Monaco Editor | VS Code's editor, code-split |
| State | Zustand (light) + React Query | Client state + server cache |
| Realtime | native WebSocket | Streams agent events |
| UI primitives | Radix UI (headless, accessible) | No heavy component library |
| Responsive | CSS breakpoints + Tailwind, single-pane → multi-pane | Mobile-first; bottom-tab nav on phones |

---

## 4. Technology Stack (final selection)

| Layer | Choice | Rationale (fast / light / modern / free) |
|-------|--------|------------------------------------------|
| Backend | **Python 3.11 + FastAPI + Uvicorn** | Async, fast, best AI ecosystem, typed via Pydantic |
| Frontend | **React 18 + TypeScript + Vite + Tailwind** | Fast builds, small bundle, modern DX |
| Models | **Groq (free), Gemini (free), Ollama (local)** | Fast + free + unlimited fallback |
| Agent | **Custom lightweight loop** | Full control, no heavy framework overhead |
| DB | **SQLite** (via SQLAlchemy) | Zero-config, light, durable |
| Vector DB | **ChromaDB** | Embedded, open source, light |
| Embeddings | **BGE-small / Ollama embeddings** | Free, local, no API key |
| Sandbox | **GitHub Codespaces + Docker fallback** | Free + isolated |
| Search | **DuckDuckGo (default) / Tavily (optional)** | Free + keyless |
| GitHub | **PyGithub / GitHub REST + git CLI** | Mature, free |
| Documents | **python-docx, openpyxl, pandas, python-pptx, pdfplumber, reportlab** | Full OOXML + PDF read/write, all free |
| Vision/OCR | **Ollama VLM / Gemini vision; Tesseract** | Free vision + OCR |
| Image gen | **Pollinations.ai / local Stable Diffusion (ComfyUI)** | Free + keyless or local |
| Charts | **matplotlib + Plotly** | Free, static + interactive |
| Deployment | **Docker Compose** | Single-command start, portable to $0 VM |

**Explicitly avoided:** heavy agent frameworks (LangChain/LlamaIndex) in the core loop — they add abstraction weight for a single-agent system; we keep the loop explicit and add libraries only where they save real work (e.g., embeddings).

---

## 5. Data Flow (primary flows)

### 5.1 Chat with tool use
```
User → UI → WS /ws/chat/{id}
        → Agent Core → Router → provider (stream tokens back as events)
        → if tool_calls: Tool Registry executes → results appended
        → final answer streamed → persisted to SQLite
```

### 5.2 Code + preview
```
Agent writes files → workspace (SQLite-backed index + FS)
  → sandbox runs dev server → backend proxies port
  → UI preview iframe loads proxy URL
```

### 5.3 RAG question
```
User adds doc → embed → ChromaDB
User asks → agent calls knowledge_query → top-k chunks → injected into prompt → answer
```

### 5.4 GitHub push
```
Agent calls git_commit → sandbox git commit → git_push (token) → GitHub
```

### 5.5 File ingestion & analysis
```
User uploads file → parse (docx/xlsx/pdf/csv/img/zip) → markdown/text + structured data
  → optionally embed into ChromaDB
  → agent answers questions / summarizes / extracts data
```

### 5.6 Conversion
```
Source file → parser → markdown interchange → writer (docx/xlsx/pdf/pptx/md/html) → workspace → preview/download
```

### 5.7 Chart generation
```
dataset → analyze_data (pandas) → generate_chart (matplotlib/plotly) → PNG/HTML → preview + download
```

---

## 6. Deployment View

```
┌───────────────────────────────────────────────┐
│  Host (laptop now; Oracle Always Free VM later)│
│                                               │
│  docker compose up                            │
│   ├── backend  (FastAPI + agent + router)     │
│   ├── frontend (served static / nginx)        │
│   ├── ollama   (optional, local models)       │
│   └── sandbox  (Docker-in-Docker, fallback)   │
└───────────────────────────────────────────────┘
```

- Layer 1 target: run on the developer's machine via Docker Compose.
- Later: identical compose file on a free ARM VM (Oracle Always Free) for 24/7 availability. All images are multi-arch.

---

## 7. Cross-Cutting Concerns

| Concern | Approach |
|---------|----------|
| Security | Sandbox isolation; workspace-root confinement; least-privilege tokens; secrets via env |
| Logging | Structured logs (JSON) to stdout; audit trail of tool calls |
| Config | Single `config.yaml` / env file for model pool, keys, sandbox mode |
| Error handling | Normalized error types; graceful degradation to local Ollama |
| Observability | `/health` endpoints; metrics (prometheus optional, later) |

---

## 8. Evolution Path (future layers)

| Layer | Scope | Architectural impact |
|-------|-------|---------------------|
| 2 | Multi-agent (orchestrator + specialists) | Agent Registry already supports multiple agents |
| 3 | Third-party apps via MCP/OAuth | New `mcp` tool + auth module |
| 4 | Self-edit + self-heal of Apex AI | File tools pointed at own repo + git rollback + watchdog |
| 5 | Fine-tuning custom models | Separate offline training pipeline |
