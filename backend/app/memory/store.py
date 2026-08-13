"""Conversation persistence on SQLite (stdlib `sqlite3`).

Chosen over SQLAlchemy for Layer 1 to keep the footprint light and the
dependency surface minimal; the schema is deliberately simple so an ORM can
be swapped in later without data migration. All access uses short-lived
connections and parameterized queries.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


def _now() -> float:
    return time.time()


class Store:
    """Durable conversation + message + knowledge storage."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _migrate(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages(conversation_id, created_at);
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_knowledge_doc
                    ON knowledge_chunks(document_id);
                """
            )
            conn.commit()
        finally:
            conn.close()

    # ---- Conversations -------------------------------------------------

    def create_conversation(self, title: str = "New conversation") -> dict[str, Any]:
        cid = str(uuid.uuid4())
        now = _now()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (cid, title, now, now),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_conversation(cid)

    def get_conversation(self, cid: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (cid,)
            ).fetchone()
        finally:
            conn.close()
        return dict(row) if row else None

    def list_conversations(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def rename_conversation(self, cid: str, title: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, _now(), cid),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_conversation(self, cid: str) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
            conn.commit()
        finally:
            conn.close()

    # ---- Messages ------------------------------------------------------

    def add_message(
        self, conversation_id: str, role: str, content: str, kind: str = "text"
    ) -> dict[str, Any]:
        mid = str(uuid.uuid4())
        now = _now()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, kind, content, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (mid, conversation_id, role, kind, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": mid, "conversation_id": conversation_id, "role": role,
                "kind": kind, "content": content, "created_at": now}

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    # ---- Knowledge chunks ----------------------------------------------

    def add_chunk(
        self, document_id: str, source: str, chunk_index: int,
        text: str, embedding: list[float],
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO knowledge_chunks "
                "(id, document_id, source, chunk_index, text, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    document_id,
                    source,
                    chunk_index,
                    text,
                    json.dumps(embedding),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def clear_document(self, document_id: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def all_chunks(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM knowledge_chunks").fetchall()
        finally:
            conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["embedding"] = json.loads(d["embedding"])
            result.append(d)
        return result
