"""Tests for specialist agents and the orchestrator's classification."""

from __future__ import annotations

from app.agent.specialists import (
    SPECIALISTS,
    REVIEWER,
    classify_and_pick,
    specialist_for,
)
from app.agent.tasks import TaskKind


def test_every_task_kind_has_specialist():
    for kind in TaskKind:
        assert kind in SPECIALISTS
        assert SPECIALISTS[kind].persona.strip()


def test_classify_and_pick_code():
    s = classify_and_pick("Build me a React app")
    assert s.name == "coder"


def test_classify_and_pick_chat():
    s = classify_and_pick("hi how are you")
    assert s.name == "generalist"


def test_classify_and_pick_data():
    s = classify_and_pick("analyze this csv")
    assert s.name == "data_analyst"


def test_coder_has_restricted_tools():
    coder = specialist_for(TaskKind.CODE)
    assert coder.tool_filter is not None
    assert "write_file" in coder.tool_filter
    assert "generate_image" not in coder.tool_filter  # coder doesn't generate images


def test_chat_has_all_tools():
    chat = specialist_for(TaskKind.CHAT)
    assert chat.tool_filter is None  # empty set → all tools


def test_reviewer_exists_with_models():
    assert REVIEWER.name == "reviewer"
    assert REVIEWER.preferred_models
    assert "{work}" in REVIEWER.persona and "{request}" in REVIEWER.persona
