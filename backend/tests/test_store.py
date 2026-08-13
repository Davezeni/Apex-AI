"""Tests for conversation persistence."""

from __future__ import annotations

from pathlib import Path

from app.memory.store import Store


def test_conversation_crud(tmp_path: Path):
    store = Store(tmp_path / "t.sqlite3")
    conv = store.create_conversation("Build an app")
    assert conv["id"]

    store.add_message(conv["id"], "user", "hello")
    store.add_message(conv["id"], "assistant", "hi there")

    messages = store.list_messages(conv["id"])
    assert [m["role"] for m in messages] == ["user", "assistant"]

    assert len(store.list_conversations()) == 1
    store.rename_conversation(conv["id"], "Renamed")
    assert store.get_conversation(conv["id"])["title"] == "Renamed"

    store.delete_conversation(conv["id"])
    assert store.list_messages(conv["id"]) == []
    assert store.list_conversations() == []
