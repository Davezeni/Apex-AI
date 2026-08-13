# Apex AI — Software Requirements Specification (SRS)

**Document ID:** AX-REQ-001
**Version:** 1.1
**Status:** Draft for review
**Date:** 2026-08-13
**Author:** Apex AI Project

---

## 1. Introduction

### 1.1 Purpose
This document defines the complete functional and non-functional requirements for **Apex AI**, a self-hosted AI agent platform. Apex AI is a full-stack software builder that lets a user converse with an AI agent that can create files, structure folders, run and preview code in an isolated sandbox, search the web, integrate with GitHub, and manage its own knowledge.

Apex AI is a **proprietary (closed-source) product**. It is designed around one governing constraint: **every dependency and component it is built on must be free and open source, permissively licensed (MIT/Apache-2.0/BSD), fast, lightweight, modern, and production-grade.** The product's own source code remains closed, and no copyleft (GPL/AGPL) components are used so that this remains legally clean.

### 1.2 Scope
Apex AI is a **single-agent system** in its first release (Layer 1), architected from day one to scale to a multi-agent system (orchestrator + specialist workers). This SRS covers the full Layer 1 scope plus the architectural hooks required for later multi-agent expansion.

**In scope (this document):**
- Conversational agent with tool use and streaming
- Multi-model router with round-robin + failover across free model sources
- Filesystem tools (create/read/edit/delete files and folders, scaffold structures)
- Code sandbox via GitHub Codespaces (with local Docker as a fallback)
- Live preview of generated code
- Web search tool
- GitHub integration (clone, commit, push, pull)
- Workspace download (zip export)
- Knowledge base / memory (RAG over user documents)
- Chat UI: sidebar, code space, thinking-step timeline, in-chat choice questions
- Health monitoring and self-healing of the platform itself
- File upload & understanding (images, documents, spreadsheets, archives)
- Vision & OCR (describe images, extract text and data from images)
- Image generation (text-to-image, image editing)
- Document & format conversion (pdf ↔ excel ↔ csv ↔ word ↔ pptx ↔ markdown)
- Data analysis & visualization (charts, graphs, statistics)
- Document authoring (SAD/SDD/PRD/README, presentation decks, citations, links, fonts)

**Out of scope (future layers, documented but not built in Layer 1):**
- Multi-agent orchestration (Layer 4)
- Self-editing of Apex AI's own source code (Layer 4)
- Third-party app access via MCP/OAuth (Layer 3)
- Fine-tuning / training of custom models (requires GPU, separate effort)

### 1.3 Definitions & Acronyms

| Term | Definition |
|------|------------|
| Agent | The autonomous loop that reasons, calls tools, and responds |
| Tool | A callable capability exposed to the model (files, web search, GitHub, …) |
| Router | Component that selects which model/provider serves a given request |
| Sandbox | Isolated environment where agent-generated code executes |
| RAG | Retrieval-Augmented Generation — grounding responses in stored documents |
| MCP | Model Context Protocol — standard for third-party tool integration |
| Workspace | The user's project filesystem managed by the agent |
| Codespace | A GitHub-hosted cloud dev container |
| OCR | Optical Character Recognition — extracting text from images |
| VLM | Vision-Language Model — a model that can "see" and describe images |
| OOXML | Office Open XML — the modern `.docx`/`.xlsx`/`.pptx` file formats |

### 1.4 References
- [02 — System Architecture Document](02-system-architecture.md)
- [03 — Software Design Document](03-software-design.md)
- [04 — Preliminary Design Review](04-preliminary-design-review.md)
- `README.md`

---

## 2. Overall Description

### 2.1 Product Perspective
Apex AI is a **self-hosted web application**. It runs as two cooperating processes (a Python backend and a web frontend), both deployable to a single machine or a free-tier VM. It has no hard dependency on any paid service at build or runtime.

### 2.2 Product Vision
> A powerful, free, open-source AI builder that any developer can run anywhere — capable of writing code, previewing it, searching the web, integrating with GitHub, and growing its own knowledge, using a rotating pool of free and open models so it never hard-fails on a rate limit.

### 2.3 User Classes

| Class | Description | Key needs |
|-------|-------------|-----------|
| Developer / Builder (primary) | Builds apps by conversing with the agent | Write code, preview, GitHub, download |
| Power user / tinkerer | Self-hosts, configures model pool | Control, extensibility, low footprint |
| (Future) Team member | Collaborates via shared workspace | Auth, shared sandboxes |

### 2.4 Operating Environment
- **Host:** Linux/macOS/Windows with Docker, or a free-tier cloud VM (Oracle Always Free recommended).
- **Browser:** Any modern evergreen browser (Chrome, Firefox, Safari, Edge).
- **Network:** Outbound HTTPS to model providers (Groq, Gemini) and GitHub; inbound access only to the local web UI (or reverse-proxied).

### 2.5 Design & Implementation Constraints
1. **100% free + open source, permissively licensed** for every runtime dependency (no GPL/AGPL components).
2. **Proprietary product:** Apex AI's own code is closed-source; only its dependencies are FOSS.
3. **Lightweight:** idle memory footprint < 512 MB; cold-start to first response < 2 s.
4. **Fast:** first token streamed to the user in < 500 ms on hosted models.
5. **Modern:** TypeScript + React frontend; async Python backend; WebSocket streaming.
6. **Mobile-first & responsive:** the UI is designed for phones first (single-pane, bottom-tab), scaling to multi-pane on larger screens.
7. **Self-hostable:** ships as Docker Compose; single-command start.
8. **Extensible:** tools and model providers are pluggable registries.

### 2.6 Assumptions & Dependencies
- The user supplies **free API keys** for hosted models (Groq, Google AI Studio). These are optional — the system must run on **Ollama (local) only** if no keys are present. Note: Google AI Studio now issues `AQ.Ab...` "authentication keys" (replacing `AIza...`); the Gemini adapter must support this format via the native Gemini SDK.
- A GitHub account is required only for Codespaces sandbox + GitHub integration features.
- Free-tier limits are subject to change by providers; model IDs are **configurable at runtime**, not hardcoded.

---

## 3. Functional Requirements

Requirements are numbered `FR-<group>-<n>` and each carries a priority: **P0** (must), **P1** (should), **P2** (nice to have).

### 3.1 Agent Core

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-AGT-1 | The system SHALL run a reasoning loop: receive a user message, decide to call zero or more tools, execute them, observe results, and produce a final response. | P0 |
| FR-AGT-2 | The loop SHALL stream the model's progress (thinking steps, tool calls, partial text) to the client in real time over WebSocket. | P0 |
| FR-AGT-3 | The loop SHALL enforce a configurable maximum number of iterations per turn to prevent infinite loops. | P0 |
| FR-AGT-4 | The system SHALL expose every capability as a registered **tool** with a name, description, and JSON schema, discoverable by the model. | P0 |
| FR-AGT-5 | The system SHALL be structured as an **agent registry** so additional agents (multi-agent expansion) can be added without rewriting the core loop. | P1 |
| FR-AGT-6 | A user SHALL be able to cancel a running agent turn at any time. | P1 |

### 3.2 Model Router

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-RTR-1 | The router SHALL support multiple providers: Groq (hosted, fast), Google Gemini (hosted), and Ollama (local, unlimited). | P0 |
| FR-RTR-2 | The router SHALL cycle through a configured model pool (round-robin) so consecutive requests spread across models. | P0 |
| FR-RTR-3 | On a rate-limit or provider error, the router SHALL automatically fail over to the next model in the pool, wrapping around indefinitely. | P0 |
| FR-RTR-4 | The router SHALL track a **cooldown** timestamp per model when rate-limited and skip cooling models. | P0 |
| FR-RTR-5 | The pool order SHALL be configurable via a settings file; model IDs SHALL NOT be hardcoded. | P0 |
| FR-RTR-6 | The router SHALL prefer higher-priority models and fall back gracefully to local Ollama as the final unlimited fallback. | P1 |
| FR-RTR-7 | The router SHALL support **structured/tool-calling** output from every provider that supports it, normalizing to a common schema. | P0 |

### 3.3 Filesystem Tools

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-FS-1 | The agent SHALL be able to create, read, update, and delete files in a workspace directory. | P0 |
| FR-FS-2 | The agent SHALL be able to create folders and scaffold nested directory structures in a single operation. | P0 |
| FR-FS-3 | The agent SHALL be able to list directory contents (a file tree). | P0 |
| FR-FS-4 | All file operations SHALL be confined to the workspace root (path-traversal protection). | P0 |
| FR-FS-5 | File changes SHALL be surfaced to the client so the "code space" view updates live. | P0 |
| FR-FS-6 | The user SHALL be able to download the entire workspace as a zip archive. | P0 |

### 3.4 Sandbox & Preview

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SBX-1 | Agent-generated code SHALL execute in an isolated sandbox, never directly on the host. | P0 |
| FR-SBX-2 | The primary sandbox backend SHALL be GitHub Codespaces; a local Docker backend SHALL be provided as an alternative. | P0 |
| FR-SBX-3 | The sandbox SHALL support running a dev server and exposing it as a **live preview** in the UI. | P0 |
| FR-SBX-4 | The preview SHALL be embedded in the browser via a proxied iframe (no localhost calls from browser code). | P0 |
| FR-SBX-5 | Sandbox state SHALL be persisted in the user's GitHub repo so work survives across sessions. | P1 |

### 3.5 Web Search

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-WEB-1 | The agent SHALL have a web search tool that returns titles, URLs, and snippets. | P0 |
| FR-WEB-2 | The default search backend SHALL be free and keyless (e.g., DuckDuckGo); a keyed provider (e.g., Tavily) SHALL be pluggable. | P0 |
| FR-WEB-3 | Search results SHALL be returned to the model as structured context, not raw HTML. | P0 |

### 3.6 GitHub Integration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-GH-1 | The user SHALL be able to authenticate with GitHub (fine-grained PAT or OAuth). | P0 |
| FR-GH-2 | The agent SHALL be able to clone an existing repository into the workspace. | P0 |
| FR-GH-3 | The agent SHALL be able to create a new repository and push workspace content to it. | P0 |
| FR-GH-4 | The agent SHALL be able to commit, push, and pull changes. | P0 |
| FR-GH-5 | All GitHub actions SHALL require explicit user confirmation the first time a credential is used. | P0 |

### 3.7 Knowledge & Memory

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-KNW-1 | The user SHALL be able to add documents to a knowledge base. | P1 |
| FR-KNW-2 | The system SHALL embed and index documents in a local vector store (ChromaDB). | P1 |
| FR-KNW-3 | The agent SHALL retrieve relevant knowledge and ground its answers (RAG). | P1 |
| FR-KNW-4 | Conversation history SHALL persist across sessions and be resumable from the sidebar. | P0 |
| FR-KNW-5 | Embeddings SHALL be produced locally or via a free endpoint (no paid embedding API required). | P1 |

### 3.8 Chat UI

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UI-1 | The UI SHALL provide a chat view with user/assistant messages and streaming text. | P0 |
| FR-UI-2 | The UI SHALL render the agent's **thinking steps** and tool calls as collapsible timeline cards. | P0 |
| FR-UI-3 | A **sidebar** SHALL list conversations and allow create/rename/delete/resume. | P0 |
| FR-UI-4 | A **code space** SHALL show the workspace file tree and an embedded code editor (Monaco). | P0 |
| FR-UI-5 | A **preview pane** SHALL render the sandbox's live app. | P0 |
| FR-UI-6 | The agent SHALL be able to ask the user **in-chat choice questions** (multi-option + free text) and pause until answered. | P1 |
| FR-UI-7 | The UI SHALL be responsive and keyboard-friendly. | P1 |
| FR-UI-8 | The UI SHALL be **mobile-first**: on small screens a single pane with bottom-tab navigation (Chat / Code / Preview); on ≥ md screens a multi-pane layout (sidebar + chat + code + preview). | P0 |
| FR-UI-9 | All interactive elements SHALL meet touch-target sizes (≥ 44 px) and support swipe gestures for pane switching on mobile. | P1 |

### 3.9 Platform Health & Self-Healing

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-HLT-1 | The backend SHALL expose a health endpoint (liveness/readiness). | P0 |
| FR-HLT-2 | A watchdog SHALL monitor CPU, memory, disk, and error rate, and log anomalies. | P1 |
| FR-HLT-3 | The system SHALL auto-restart failed subcomponents (e.g., sandbox, embedding worker). | P1 |
| FR-HLT-4 | The system SHALL log all agent actions to an audit trail for review. | P0 |

### 3.10 File Ingestion & Understanding

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-FILE-1 | The user SHALL be able to upload files (drag-and-drop / multipart): text, Markdown, JSON, CSV, PDF, Word, Excel, PowerPoint, images, and zip archives. | P0 |
| FR-FILE-2 | The system SHALL extract and parse the content of uploaded documents (docx, xlsx, pptx, pdf, csv, txt, md, html, json). | P0 |
| FR-FILE-3 | The system SHALL extract the contents of zip archives (including nested archives) into the workspace. | P0 |
| FR-FILE-4 | The agent SHALL produce a description/summary of any uploaded file. | P0 |
| FR-FILE-5 | The agent SHALL extract structured data (tables, key–value pairs, metadata) from uploaded files. | P0 |
| FR-FILE-6 | The user SHALL be able to download any generated file, or the whole workspace as a zip. | P0 |
| FR-FILE-7 | Uploaded files SHALL be stored within the workspace and made visible in the code-space file tree. | P0 |

### 3.11 Vision & OCR

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-VIS-1 | The agent SHALL describe the content of an uploaded image (via a vision-capable model). | P0 |
| FR-VIS-2 | The agent SHALL extract text from images and scanned documents (OCR). | P0 |
| FR-VIS-3 | The agent SHALL abstract/derive data from images (e.g., read a table or chart back into structured data). | P1 |
| FR-VIS-4 | Vision and OCR SHALL run free — using local vision models (Ollama) and/or a free hosted vision tier (Gemini). | P0 |

### 3.12 Image Generation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-IMG-1 | The agent SHALL generate images from text prompts (free, keyless or local). | P1 |
| FR-IMG-2 | The agent SHALL edit/restyle existing images on request. | P2 |
| FR-IMG-3 | Generated images SHALL be saved to the workspace, shown in the UI, and downloadable. | P1 |

### 3.13 Document & Format Conversion

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DOC-1 | The agent SHALL convert between file formats: pdf, xlsx, csv, docx, pptx, md, html. | P0 |
| FR-DOC-2 | The agent SHALL copy data from one file type into another (e.g., CSV → XLSX → PDF) preserving tables and structure. | P0 |
| FR-DOC-3 | Conversions SHALL produce valid OOXML files (.docx/.xlsx/.pptx) so they preview and download correctly. | P0 |
| FR-DOC-4 | The agent SHALL be able to merge, split, and reformat documents (e.g., concatenate CSVs, split a PDF). | P1 |

### 3.14 Data Analysis & Visualization

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DAT-1 | The agent SHALL analyze data files and answer questions about them ("analysis about anything" the user provides). | P0 |
| FR-DAT-2 | The agent SHALL generate charts and graphs — bar, line, pie, scatter, histogram — as images or interactive HTML. | P0 |
| FR-DAT-3 | The agent SHALL compute statistics and summaries over datasets. | P1 |
| FR-DAT-4 | Charts SHALL be renderable in the UI preview and downloadable as images/HTML. | P0 |

### 3.15 Document Authoring

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-AUT-1 | The agent SHALL generate engineering documents (SAD, SDD, SRS/PRD, README) from structured templates. | P0 |
| FR-AUT-2 | The agent SHALL generate presentation decks (.pptx) with slide titles and content. | P1 |
| FR-AUT-3 | The agent SHALL apply font styles, headings, and formatting to generated documents. | P1 |
| FR-AUT-4 | The agent SHALL generate internal (anchor) and external hyperlinks in documents. | P1 |
| FR-AUT-5 | The agent SHALL produce quotations/citations with tracked sources (for web search and document grounding). | P1 |
| FR-AUT-6 | Generated documents SHALL be written as Markdown and/or OOXML and previewable in the UI. | P0 |

---

## 4. Non-Functional Requirements

### 4.1 Performance
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-P-1 | Time-to-first-token (hosted models) | < 500 ms |
| NFR-P-2 | File tool round-trip (create + read) | < 50 ms |
| NFR-P-3 | UI bundle size (gzipped, first load) | < 400 KB (code-split) |
| NFR-P-4 | Idle memory footprint | < 512 MB |
| NFR-P-5 | Cold start to interactive | < 2 s |

### 4.2 Security
| ID | Requirement |
|----|-------------|
| NFR-S-1 | Generated code executes only inside the sandbox; never on the host. |
| NFR-S-2 | All filesystem tools enforce workspace-root confinement. |
| NFR-S-3 | Secrets (API keys, tokens) are stored in environment variables or a git-ignored local file, never in the repo or logs. |
| NFR-S-4 | GitHub credentials use least-privilege scopes; every credential use is user-confirmed. |
| NFR-S-5 | The web UI binds to localhost by default; remote access requires explicit user opt-in + reverse proxy. |
| NFR-S-6 | All inputs (user + model + search results) are validated/sanitized. |

### 4.3 Reliability & Availability
| ID | Requirement |
|----|-------------|
| NFR-A-1 | The system degrades gracefully: if all hosted models are rate-limited, it falls back to local Ollama; if Ollama is down, it returns a clear error rather than hanging. |
| NFR-A-2 | Conversations are durable (SQLite) and survive restarts. |
| NFR-A-3 | The agent loop has bounded retries and a hard iteration cap. |

### 4.4 Maintainability & Extensibility
| ID | Requirement |
|----|-------------|
| NFR-M-1 | New tools are added by registering a single decorated class/function — no core changes. |
| NFR-M-2 | New model providers are added by implementing one adapter interface. |
| NFR-M-3 | The codebase is typed (TypeScript frontend; Python type hints + Pydantic). |
| NFR-M-4 | The system is structured so a multi-agent layer can be added without rewriting the loop. |

### 4.5 Portability
| ID | Requirement |
|----|-------------|
| NFR-PT-1 | The full stack SHALL run via `docker compose up` on any Linux host. |
| NFR-PT-2 | The stack SHALL be deployable to a free-tier ARM VM (Oracle Always Free). |

### 4.6 Usability (Mobile-first)
| ID | Requirement |
|----|-------------|
| NFR-U-1 | Primary user flows (chat, view files, view preview) SHALL be fully usable on a 360 px-wide viewport without horizontal scroll. |
| NFR-U-2 | The layout SHALL adapt breakpoints: single-pane (mobile) → two-pane (tablet) → multi-pane (desktop). |
| NFR-U-3 | The UI SHALL load and be interactive on mid-range mobile hardware (Lighthouse mobile performance score ≥ 80). |

---

## 5. Traceability Summary

| Module | Key FRs | Key NFRs |
|--------|---------|----------|
| Agent core | FR-AGT-1..6 | NFR-A-3 |
| Model router | FR-RTR-1..7 | NFR-A-1 |
| Filesystem | FR-FS-1..6 | NFR-S-2 |
| Sandbox | FR-SBX-1..5 | NFR-S-1 |
| Web search | FR-WEB-1..3 | — |
| GitHub | FR-GH-1..5 | NFR-S-4 |
| Knowledge | FR-KNW-1..5 | NFR-A-2 |
| Chat UI | FR-UI-1..7 | NFR-P-3 |
| Health | FR-HLT-1..4 | NFR-A-1 |
| File ingestion | FR-FILE-1..7 | NFR-S-6 |
| Vision & OCR | FR-VIS-1..4 | — |
| Image generation | FR-IMG-1..3 | — |
| Format conversion | FR-DOC-1..4 | NFR-S-6 |
| Data & viz | FR-DAT-1..4 | NFR-P-1 |
| Authoring | FR-AUT-1..6 | NFR-S-6 |

---

## 6. Acceptance Criteria (summary)

The Layer 1 release is accepted when:
1. A user can chat with the agent, watch it think, and receive streamed answers.
2. The agent can create a multi-file project, run it in a sandbox, and show a live preview.
3. The agent survives a simulated rate-limit on its primary model and transparently continues on the next model in the pool.
4. The user can download the workspace as a zip and push it to a new GitHub repo.
5. The agent can answer a question grounded in an uploaded document (RAG).
6. The agent can ingest an uploaded PDF/XLSX/CSV, summarize it, and answer questions about it.
7. The agent can describe an uploaded image and extract text from it (OCR).
8. The agent can convert a CSV to XLSX and to PDF, preserving table structure.
9. The agent can generate a chart from a dataset and show it in the preview.
10. The agent can generate a complete SAD/SDD/PRD/README document set on request.
11. The entire stack starts with a single `docker compose up` and runs on a free-tier VM.
