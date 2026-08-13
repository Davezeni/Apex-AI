"""Knowledge tools: add documents to the knowledge base and query it (RAG)."""

from __future__ import annotations

import uuid
from typing import Any

from .base import Tool, ToolContext, ToolResult


class KnowledgeAddTool(Tool):
    name = "knowledge_add"
    description = (
        "Add a document's text to the knowledge base so it can be retrieved later. "
        "Call this before answering questions grounded in that document."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Filename or label"},
            "text": {"type": "string", "description": "Full document text"},
        },
        "required": ["source", "text"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        if ctx.knowledge is None:
            return ToolResult(ok=False, summary="knowledge base not configured")

        source = args.get("source")
        text = args.get("text")
        if not isinstance(source, str) or not isinstance(text, str):
            return ToolResult(ok=False, summary="source and text must be strings")

        document_id = str(uuid.uuid4())
        try:
            n = await ctx.knowledge.add(document_id, source, text)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"knowledge add failed: {exc}")
        return ToolResult(ok=True, summary=f"indexed {n} chunk(s) from {source}")


class KnowledgeQueryTool(Tool):
    name = "knowledge_query"
    description = (
        "Retrieve the most relevant stored document chunks for a query. "
        "Use to ground an answer in previously added documents."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer"},
        },
        "required": ["query"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        if ctx.knowledge is None:
            return ToolResult(ok=False, summary="knowledge base not configured")

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(ok=False, summary="query must be a non-empty string")

        top_k = args.get("top_k", 4)
        top_k = int(top_k) if isinstance(top_k, (int, float)) else 4
        top_k = max(1, min(10, top_k))

        try:
            chunks = await ctx.knowledge.query(query, top_k)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"knowledge query failed: {exc}")

        if not chunks:
            return ToolResult(ok=True, summary="no relevant chunks", content="(no matches)")

        lines = [f"Top {len(chunks)} relevant chunk(s):"]
        for c in chunks:
            lines.append(f"\n[{c.source}] (score {c.score})\n{c.text}")
        return ToolResult(ok=True, summary=f"{len(chunks)} chunk(s)", content="\n".join(lines))
