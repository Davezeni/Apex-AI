"""Knowledge base with retrieval (RAG).

Embeddings are pluggable:
- `HashEmbedder` — deterministic, dependency-free bag-of-words hashing vector
  (default; useful for keyword-overlap retrieval and offline testing).
- `OllamaEmbedder` — real semantic embeddings via a local Ollama model.

Chunks are stored in SQLite (via `Store`) and ranked by cosine similarity.
A proper vector DB (ChromaDB) can replace the retrieval layer later without
changing the public interface.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from .store import Store

DIM = 256


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Deterministic hashing embedder (no model download, fully offline)."""

    _TOKEN = re.compile(r"[A-Za-z0-9_]+")

    async def embed(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        tokens = self._TOKEN.findall(text.lower())
        for tok in tokens:
            h = int.from_bytes(hashlib.md5(tok.encode()).digest()[:2], "big")
            vec[h % DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OllamaEmbedder:
    """Semantic embeddings via a local Ollama server (e.g. nomic-embed-text)."""

    def __init__(self, base_url: str, model: str = "nomic-embed-text") -> None:
        self._url = base_url.rstrip("/")
        self._model = model

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]


@dataclass
class RetrievedChunk:
    document_id: str
    source: str
    text: str
    score: float


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _chunk_text(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


class KnowledgeBase:
    """Stores documents as embedded chunks and retrieves relevant ones."""

    def __init__(self, store: Store, embedder: Embedder) -> None:
        self._store = store
        self._embedder = embedder

    async def add(self, document_id: str, source: str, text: str) -> int:
        self._store.clear_document(document_id)
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            emb = await self._embedder.embed(chunk)
            self._store.add_chunk(document_id, source, i, chunk, emb)
        return len(chunks)

    async def query(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        qvec = await self._embedder.embed(query)
        scored = []
        for chunk in self._store.all_chunks():
            score = _cosine(qvec, chunk["embedding"])
            scored.append((score, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            RetrievedChunk(
                document_id=c["document_id"],
                source=c["source"],
                text=c["text"],
                score=round(score, 4),
            )
            for score, c in scored[:top_k]
            if score > 0.0
        ]
