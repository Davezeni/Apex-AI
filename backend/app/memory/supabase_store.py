"""Supabase-backed store (PostgREST) — same synchronous interface as Store.

Used for persistent storage that survives redeploys (Render's ephemeral
filesystem wipes SQLite). The backend uses the service_role key, which
bypasses RLS; the key never leaves the server.

Interface mirrors `memory/store.py` exactly (synchronous), so the app switches
between SQLite (local) and Supabase (deployed) via STORE_BACKEND with no
changes to call sites.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx


class SupabaseStore:
    """Conversation + message + knowledge storage on Supabase via PostgREST."""

    def __init__(self, url: str, service_role_key: str, timeout: float = 30.0) -> None:
        self._client = httpx.Client(
            base_url=url.rstrip("/"),
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
            },
            timeout=timeout,
        )

    @staticmethod
    def _match_params(match: dict) -> dict:
        # PostgREST equality filter: column=eq.value
        return {k: f"eq.{v}" for k, v in match.items()}

    def _get(self, table: str, params: dict) -> list[dict]:
        resp = self._client.get(f"/{table}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, table: str, body: dict) -> dict:
        resp = self._client.post(
            f"/{table}",
            json=body,
            headers={"Prefer": "return=representation"},
        )
        resp.raise_for_status()
        return resp.json()[0]

    def _patch(self, table: str, match: dict, body: dict) -> None:
        self._client.patch(f"/{table}", params=self._match_params(match), json=body).raise_for_status()

    def _delete(self, table: str, match: dict) -> None:
        self._client.delete(f"/{table}", params=self._match_params(match)).raise_for_status()

    # ---- Conversations -------------------------------------------------

    def create_conversation(self, title: str = "New conversation") -> dict:
        cid = str(uuid.uuid4())
        now = time.time()
        row = self._post("conversations", {"id": cid, "title": title, "created_at": now, "updated_at": now})
        return self._conv_to_dict(row)

    def get_conversation(self, cid: str) -> dict | None:
        rows = self._get("conversations", {"id": f"eq.{cid}"})
        return self._conv_to_dict(rows[0]) if rows else None

    def list_conversations(self) -> list[dict]:
        rows = self._get("conversations", {"order": "updated_at.desc"})
        return [self._conv_to_dict(r) for r in rows]

    def rename_conversation(self, cid: str, title: str) -> None:
        self._patch("conversations", {"id": cid}, {"title": title, "updated_at": time.time()})

    def delete_conversation(self, cid: str) -> None:
        self._delete("conversations", {"id": cid})

    @staticmethod
    def _conv_to_dict(row: dict) -> dict:
        return {"id": row["id"], "title": row["title"], "created_at": row["created_at"], "updated_at": row["updated_at"]}

    # ---- Messages ------------------------------------------------------

    def add_message(self, conversation_id: str, role: str, content: str, kind: str = "text") -> dict:
        mid = str(uuid.uuid4())
        now = time.time()
        self._post(
            "messages",
            {"id": mid, "conversation_id": conversation_id, "role": role, "kind": kind, "content": content, "created_at": now},
        )
        self._patch("conversations", {"id": conversation_id}, {"updated_at": now})
        return {"id": mid, "conversation_id": conversation_id, "role": role, "kind": kind, "content": content, "created_at": now}

    def list_messages(self, conversation_id: str) -> list[dict]:
        rows = self._get("messages", {"conversation_id": f"eq.{conversation_id}", "order": "created_at.asc"})
        return [
            {"id": r["id"], "conversation_id": r["conversation_id"], "role": r["role"], "kind": r["kind"], "content": r["content"], "created_at": r["created_at"]}
            for r in rows
        ]

    # ---- Knowledge chunks ----------------------------------------------

    def add_chunk(self, document_id: str, source: str, chunk_index: int, text: str, embedding: list[float]) -> None:
        self._post(
            "knowledge_chunks",
            {"id": str(uuid.uuid4()), "document_id": document_id, "source": source, "chunk_index": chunk_index, "text": text, "embedding": json.dumps(embedding)},
        )

    def clear_document(self, document_id: str) -> None:
        self._delete("knowledge_chunks", {"document_id": document_id})

    def all_chunks(self) -> list[dict]:
        rows = self._get("knowledge_chunks", {"select": "*"})
        result = []
        for r in rows:
            d = {"id": r["id"], "document_id": r["document_id"], "source": r["source"], "chunk_index": r["chunk_index"], "text": r["text"], "embedding": json.loads(r["embedding"])}
            result.append(d)
        return result

    def close(self) -> None:
        self._client.close()
