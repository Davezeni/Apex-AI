# Apex AI — Preliminary Design Review (PDR)

**Document ID:** AX-PDR-001
**Version:** 1.1
**Date:** 2026-08-13
**Review status:** Design baseline proposed — awaiting approval to proceed to build.

---

## 1. Purpose

This PDR presents the design baseline for **Apex AI** (Layer 1) for review. It documents the key design decisions, the alternatives that were considered and rejected, the identified risks and their mitigations, and the open questions requiring resolution before or during construction. It is the decision record that complements [01-requirements.md](01-requirements.md), [02-system-architecture.md](02-system-architecture.md), and [03-software-design.md](03-software-design.md).

---

## 2. Design Summary (baseline)

Apex AI Layer 1 is a **self-hosted, modular-monolith AI agent**:

- **Backend:** Python 3.11 + FastAPI, async, WebSocket streaming.
- **Frontend:** React 18 + TypeScript + Vite + Tailwind, Monaco editor.
- **Model layer:** multi-provider router (Groq free, Gemini free, Ollama local) with round-robin + failover + cooldown.
- **Tools:** filesystem, sandbox run, web search, GitHub, knowledge/RAG, ask_user, export.
- **Sandbox:** GitHub Codespaces (primary), local Docker (fallback).
- **Memory:** SQLite (conversations) + ChromaDB (vector/RAG).
- **Deployment:** Docker Compose; portable to a free ARM VM.

The baseline satisfies all P0 requirements in the SRS.

---

## 3. Key Design Decisions (ADR-style)

| # | Decision | Alternatives considered | Rationale |
|---|----------|------------------------|-----------|
| D1 | **Custom lightweight agent loop** instead of LangChain/LlamaIndex | LangChain, LlamaIndex, CrewAI, OpenAI Agents SDK | Full control, zero framework overhead, lighter runtime, deeper understanding; libraries added only where needed (embeddings). A single-agent loop is ~200 lines. |
| D2 | **Python backend + React frontend** (two languages) | Full TypeScript (Next.js), Python-only (Streamlit) | Python is strongest for LLM tooling; React gives the richest UI (Monaco, streaming, panes). Trade-off (two languages) accepted for best-of-both. |
| D3 | **Modular monolith**, not microservices | Microservices, serverless functions | Single-user scale needs no service split; module boundaries allow later extraction. Lower ops cost. |
| D4 | **Multi-provider router** (Groq+Gemini+Ollama) | Single provider; paid API only | Free + fast + unlimited fallback; the router is the mechanism to defeat free-tier rate limits (a core user requirement). |
| D5 | **GitHub Codespaces primary sandbox, Docker fallback** | E2B, WebContainers, Docker-only | User's stated preference; free; persistent (tied to a repo); Docker kept as self-hosted fallback for portability. |
| D6 | **SQLite** over Postgres | Postgres, MongoDB | Zero-config, light, durable, single-file; sufficient at Layer 1; swap via SQLAlchemy later. |
| D7 | **ChromaDB** over pgvector/Qdrant | pgvector, Qdrant, FAISS | Embedded, no server, open source, Python-native. |
| D8 | **DuckDuckGo** default search | Tavily, Serper, self-hosted SearXNG | Free and keyless; Tavily left pluggable for quality later. |
| D9 | **PAT-based GitHub auth first** | OAuth flow | Simpler, least-privilege scopes, user-confirmed; OAuth deferred. |
| D10 | **WebSocket event streaming** | SSE, polling | Bidirectional (user input mid-turn, cancel), one connection, low latency. |
| D11 | **Markdown as the interchange format** for all documents | Direct converter-per-pair | O(N) adapters vs O(N²) converters; every doc feature (docs, decks, citations, links) reads/writes one format; renders to md/docx/pptx/pdf/html. |
| D12 | **Local + free hosted vision/image-gen** (Ollama VLM / Gemini vision; Pollinations.ai / ComfyUI) | Paid vision APIs (GPT-4o, Claude vision) | Keeps the "free + open" constraint; falls back gracefully; vision/image-gen are tools, so providers are swappable. |
| D13 | **pandas + openpyxl/python-docx/python-pptx/pdfplumber** for conversion | Headless LibreOffice (UNO), pandoc-only | Lighter footprint, pure-Python where possible, no subprocess Office install; pandoc optional for extra formats. |
| D14 | **Proprietary product on permissive FOSS components only** (no GPL/AGPL) | Open-source the product; or use any-license libs | User's decision: Apex AI stays closed-source; every dependency is MIT/Apache-2.0/BSD so no copyleft obligation attaches. AGPL (e.g., some DBs) is explicitly banned. |
| D15 | **Mobile-first responsive UI** (single-pane + bottom-tab → multi-pane) | Desktop-first with responsive tweaks | User's decision: design for phones first, then enhance on larger screens; avoids retrofitting mobile later. |

---

## 4. Requirements Coverage

All P0 requirements trace to at least one design component (see SRS §5 traceability matrix). No P0 requirement is unimplementable in the baseline. P1/P2 items are scoped but not blockers.

---

## 5. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Free-tier limits change / providers deprecate models | High | Medium | Model IDs config-driven, not hardcoded; router fails over; local Ollama is the unlimited floor. |
| R2 | Free tiers cannot match frontier-model reasoning quality | High | Medium | Accept for Layer 1; single config line to add a paid provider later; multi-model review (Layer 2) raises effective quality. |
| R3 | Codespaces API/CLI friction (auth, latency, limits) | Medium | Medium | Abstract behind `Sandbox` interface; Docker fallback fully implemented and tested. |
| R4 | Security risk of running generated code | Medium | High | Strict sandbox isolation; no host execution; workspace-root confinement; least-privilege tokens. |
| R5 | Multi-agent complexity introduced too early | Medium | Medium | Layer 1 is explicitly single-agent; Agent Registry is a passive hook, not active complexity. |
| R6 | Feature creep beyond Layer 1 scope | High | Medium | SRS §1.2 explicitly scopes out-of-scope items; PDR is the baseline gate. |
| R7 | Oracle/VM signup friction or capacity issues | Medium | Low | Deployable on any Linux host; Codespaces/Docker don't depend on the VM. |
| R8 | Local embedding model footprint on constrained host | Medium | Low | Small model (BGE-small) default; Ollama embeddings as alternative; embeddings deferred (P1). |
| R9 | PDF parsing fidelity (complex layouts/tables) | Medium | Medium | Use pdfplumber/PyMuPDF; fall back to vision-based extraction for scanned/layout-heavy PDFs; flag imperfect extractions to the user. |
| R10 | Free image-gen / vision endpoints change or throttle | High | Medium | Provider-agnostic tool interface; local ComfyUI/Ollama VLM as the always-available fallback. |
| R11 | Conversion fidelity loss across formats | Medium | Medium | Markdown interchange is lossy by design for rich formatting; document supported round-trips per format; preserve tables/headings as the first-class structures. |
| R12 | Uploaded-file safety (malicious docs/archives) | Medium | High | Parse in the sandbox; zip-bomb/path-traversal guards on extraction; size limits; treat all parsed content as untrusted data. |

---

## 6. Performance & Footprint Budget

| Metric | Budget | Risk if exceeded |
|--------|--------|------------------|
| Backend idle RAM | < 200 MB | Doesn't fit Oracle free tier comfortably |
| Full stack idle RAM (no local model) | < 512 MB | OK |
| With Ollama 14B loaded | 8–16 GB | Only on a capable host; optional |
| Frontend gzip bundle | < 400 KB | Slower load; mitigated by code-splitting Monaco |

---

## 7. Open Questions

| # | Question | Owner | Needed by |
|---|----------|-------|-----------|
| Q1 | Confirm current free-tier model IDs on Groq/Gemini | Build team | Router implementation |
| Q9 | Gemini `AQ.` auth-key compatibility (native SDK only) | Build team | Gemini adapter |
| Q2 | `gh` CLI vs Codespaces REST API for `run_command` | Build team | Sandbox implementation |
| Q3 | Embedding model default (local BGE-small vs Ollama) | Build team | RAG (P1) |
| Q4 | GitHub auth: PAT-only for Layer 1 confirmed? | User | GitHub integration |
| Q5 | Target host for first deployment (local laptop vs VM) | User | Deployment guide |
| Q6 | Vision default: local Ollama VLM vs free Gemini vision? | Build team | Vision/OCR |
| Q7 | Image-gen default: Pollinations.ai (keyless) vs local ComfyUI? | Build team | Image generation |
| Q8 | Which document templates ship in Layer 1 (SAD/SDD/PRD/README + more)? | User | Authoring |

> **Recommendations (pending user confirmation):**
> - Q4 → **PAT-only** for Layer 1.
> - Q6 → **Gemini free tier primary, Ollama VLM fallback.**
> - Q7 → **Pollinations.ai primary, local ComfyUI later.**
> - Q8 → **SAD, SDD, PRD/SRS, README first** (+ `.pptx` deck second).
> - Q5 → **local laptop first, then Oracle free VM.**

---

## 8. Verification Plan (acceptance → SRS §6)

1. Chat + streamed thinking steps + tool cards render correctly.
2. Agent scaffolds a multi-file project, runs it in the sandbox, preview loads in iframe.
3. Simulate rate-limit on primary model → router transparently continues on next pool entry.
4. Workspace zips and downloads; new GitHub repo created and pushed.
5. RAG: answer grounded in an uploaded document with citation of source chunk.
6. `docker compose up` from clean checkout → usable UI in < 2 min.
7. UI is fully usable at 360 px width (single-pane, bottom-tab nav) and expands to multi-pane on desktop.
8. No GPL/AGPL dependency appears in the dependency lockfiles (license audit passes).

---

## 9. Recommendation

**Proceed to build Layer 1** against this baseline. Construction order:

1. Backend skeleton: config, FastAPI, WS channel, agent loop, router (+3 provider adapters), filesystem + web-search tools.
2. Frontend skeleton: chat + streaming + sidebar + code space (file tree + Monaco).
3. Sandbox (Docker fallback first, then Codespaces) + preview proxy + export.
4. GitHub integration + knowledge/RAG + ask_user.
5. Health/watchdog + Docker Compose + deployment guide.

---

## 10. Approval

| Role | Status |
|------|--------|
| Design baseline | Proposed |
| User / sponsor | Pending |
| Proceed to build | Pending approval |
