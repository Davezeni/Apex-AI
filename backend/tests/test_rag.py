"""Tests for the knowledge base (RAG) with the deterministic HashEmbedder."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.memory.rag import HashEmbedder, KnowledgeBase
from app.memory.store import Store


@pytest.fixture
def kb(tmp_path: Path) -> KnowledgeBase:
    store = Store(tmp_path / "kb.sqlite3")
    return KnowledgeBase(store, HashEmbedder())


@pytest.mark.asyncio
async def test_add_and_retrieve(kb):
    n = await kb.add("doc1", "plan.txt", "The launch plan is to ship by September.")
    assert n >= 1

    results = await kb.query("when do we ship?")
    assert results
    assert results[0].document_id == "doc1"
    assert "September" in results[0].text


@pytest.mark.asyncio
async def test_add_replaces_existing_document(kb):
    await kb.add("doc1", "a.txt", "alpha beta gamma")
    await kb.add("doc1", "a.txt", "completely different content here")
    chunks = kb._store.all_chunks()
    doc_ids = {c["document_id"] for c in chunks}
    # Only one document should remain (chunks replaced, not duplicated).
    assert doc_ids == {"doc1"}
