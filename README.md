# Apex AI

**A self-hosted AI agent for building software — proprietary, built entirely on free and open-source stacks.**

Apex AI is a full-stack AI builder you can run anywhere. Chat with an agent that writes code, structures projects, runs them in an isolated sandbox, previews the result, searches the web, and integrates with GitHub — powered entirely by **free and open-source models and libraries** that rotate automatically so a rate limit never stops you.

> ⚡ Fast · 🪶 Lightweight · 🧩 Modern · 💪 Strong · 📱 Mobile-first & responsive
>
> **Licensing:** Apex AI is a **proprietary (closed-source) product**. It is built only on **permissively-licensed** (MIT/Apache-2.0/BSD) free and open-source components, so it can remain closed-source with no copyleft obligation. No GPL/AGPL dependencies are used.

---

## ✨ Features

- **Chat agent with tool use** — a reasoning loop that thinks, acts, and streams its progress live.
- **Multi-model router** — cycles through Groq, Google Gemini, and local Ollama; auto-fails-over on rate limits and wraps around indefinitely (your "1-2-3-4-5-6-1-2-3" circle).
- **File & folder tools** — create, read, edit, delete, and scaffold nested project structures.
- **Sandboxed execution** — generated code runs in **GitHub Codespaces** (or local Docker), never on your host.
- **Live preview** — see the app the agent builds, right in the UI.
- **Web search** — free, keyless search (DuckDuckGo) with pluggable providers.
- **GitHub integration** — clone, commit, push, pull, create repos.
- **Knowledge base (RAG)** — point it at your documents and get grounded answers.
- **File upload & understanding** — upload images, PDFs, Word, Excel, PowerPoint, CSV, and zip archives; the agent parses, summarizes, and extracts structured data from them.
- **Vision & OCR** — describe images and pull text/data out of them.
- **Image generation** — text-to-image and image editing (free, keyless or local).
- **Format conversion** — copy data between PDF, Excel, CSV, Word, PowerPoint, Markdown, and HTML.
- **Data analysis & charts** — analyze anything, and generate bar/line/pie/scatter charts (images or interactive HTML).
- **Document authoring** — generate SAD, SDD, PRD, README, and presentation decks, with font styling, internal/external links, and cited quotations.
- **Workspace download** — export any file or the whole workspace as a zip.
- **Modern UI** — sidebar, code space (Monaco editor), thinking-step timeline, and in-chat choice questions. **Mobile-first and responsive**: single-pane with bottom-tab navigation (Chat / Code / Preview) on phones, expanding to a multi-pane layout on desktop.
- **Self-hosted & portable** — runs via a single `docker compose up`; fits on a free-tier VM.

## 🏗 Architecture

```
React + TypeScript + Vite + Tailwind   (frontend)
              │  REST + WebSocket
FastAPI + async Python                 (backend)
   ├── Agent core      (reason → act → observe loop)
   ├── Model router    (Groq / Gemini / Ollama, failover + cooldown)
   ├── Tool registry   (files, sandbox, search, GitHub, RAG, ask_user,
   │                     upload, vision/OCR, image gen, conversion,
   │                     charts, document authoring)
   ├── Memory          (SQLite conversations + ChromaDB vectors)
   └── Health/watchdog
              │
   Sandbox = GitHub Codespaces (primary) · Docker (fallback)
```

Full details in [`docs/`](docs/):

| Document | What it covers |
|----------|----------------|
| [`01-requirements.md`](docs/01-requirements.md) | Full functional + non-functional requirements (SRS) |
| [`02-system-architecture.md`](docs/02-system-architecture.md) | High-level architecture & stack decisions (SAD) |
| [`03-software-design.md`](docs/03-software-design.md) | Detailed low-level design, APIs, data models (SDD) |
| [`04-preliminary-design-review.md`](docs/04-preliminary-design-review.md) | Decisions, risks, open questions (PDR) |

## 🚀 Quick start

```bash
git clone https://github.com/Davezeni/Apex-AI.git
cd Apex-AI
cp .env.example .env              # add free API keys (optional)
cp config.example.yaml config.yaml
docker compose up                  # backend + frontend (+ optional ollama/sandbox)
# open http://localhost:3000
```

**No API keys?** Run with local Ollama only (`ollama pull qwen2.5:14b`) and Apex AI works fully offline and privately. Development without Docker:

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## ✅ What's built (Layer 1 core)

| Area | Status |
|------|--------|
| Agent loop (reason → act → observe) with streaming events | ✅ |
| Multi-model router (Groq/Gemini/Ollama; round-robin + failover + cooldown) | ✅ unit-tested |
| Filesystem tools (create/read/edit/delete/list/scaffold, traversal-guarded) | ✅ unit-tested |
| Sandbox abstraction (Docker + Codespaces backends) | ✅ (needs live host to verify) |
| Web search (DuckDuckGo keyless + Tavily) | ✅ |
| GitHub (create repo, clone/commit/push/pull) | ✅ (needs live PAT) |
| Knowledge base / RAG (pluggable embedder, offline hash + Ollama) | ✅ unit-tested |
| Document conversion (csv/xlsx/docx/md/html/json ↔ Markdown) | ✅ unit-tested |
| Conversation persistence (SQLite) + workspace export/upload | ✅ |
| WebSocket + HTTP chat, REST API | ✅ |
| Frontend (React/Vite/Tailwind, mobile-first, chat/code/preview) | ✅ builds clean |
| Docker Compose + Dockerfiles | ✅ |

**Not yet built (next increments):** live model smoke test, PDF/PPTX read-write, image generation, vision/OCR wiring, charts, document-authoring templates, Codespaces REST integration, multi-agent layer.

## 🧠 Model pool (configurable)

```yaml
models:
  pool:
    - { provider: groq,   model: "llama-3.3-70b-versatile", priority: 1 }
    - { provider: gemini, model: "gemini-2.0-flash",        priority: 2 }
    - { provider: groq,   model: "qwen-2.5-32b",            priority: 3 }
    - { provider: ollama, model: "qwen2.5:14b",             priority: 9 }  # unlimited fallback
```

Model IDs are config-driven because providers update catalogs often. Local Ollama is always the final fallback, so the pool never hard-fails.

## 🔐 Security model

- Generated code runs **only inside the sandbox** (Codespaces/Docker).
- Filesystem tools are confined to the workspace root (path-traversal guard).
- Secrets live in environment variables / git-ignored files, never in logs or the repo.
- GitHub uses least-privilege tokens, with user confirmation on first use.
- The UI binds to localhost by default.

## 🗺 Roadmap

| Layer | Scope |
|-------|-------|
| **1 (now)** | Single agent: chat, router, file tools, sandbox + preview, search, GitHub, export, RAG, health |
| **2** | Multi-agent (orchestrator + specialist workers), multi-model review |
| **3** | Third-party apps via MCP/OAuth |
| **4** | Self-edit, self-heal, and security monitoring of Apex AI itself |
| **5** | Fine-tuning custom models (separate GPU pipeline) |

## 📜 License

**Proprietary — all rights reserved.** Apex AI's own source code is closed. It is built on permissively-licensed (MIT/Apache-2.0/BSD) free and open-source components, which impose no copyleft obligations on the product. No GPL/AGPL code is linked or bundled.

## 🙌 Status

**Phase:** Layer 1 core built and unit-tested (16 tests passing). Backend (FastAPI agent + router + tools + persistence + RAG + conversion), frontend (React, mobile-first), and Docker Compose deployment are in place. Live model inference, sandbox execution, and GitHub operations still need a host-side smoke test with real credentials.

---

*Proprietary product, open-source foundation.*
