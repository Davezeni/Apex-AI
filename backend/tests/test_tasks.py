"""Tests for task classification and personas."""

from __future__ import annotations

from app.agent.tasks import TaskKind, classify, persona_for, preferred_models


def test_greeting_is_chat():
    c = classify("Hi there")
    assert c.kind == TaskKind.CHAT


def test_casual_is_chat():
    c = classify("hey how are you doing today?")
    assert c.kind == TaskKind.CHAT


def test_code_request():
    c = classify("Build me a Python API with FastAPI")
    assert c.kind == TaskKind.CODE


def test_math_request():
    c = classify("Solve this equation: x^2 + 3x + 2 = 0")
    assert c.kind == TaskKind.MATH


def test_design_request():
    c = classify("Design a landing page with a modern color palette")
    assert c.kind == TaskKind.DESIGN


def test_data_request():
    c = classify("Analyze this CSV data and make a chart")
    assert c.kind == TaskKind.DATA


def test_general_fallback():
    c = classify("tell me something interesting")
    assert c.kind in (TaskKind.GENERAL, TaskKind.CHAT)


def test_personas_differ():
    assert persona_for(TaskKind.CHAT) != persona_for(TaskKind.CODE)
    assert "friendly" in persona_for(TaskKind.CHAT).lower()
    assert "engineer" in persona_for(TaskKind.CODE).lower()


def test_preferred_models_are_in_pool_style():
    models = preferred_models(TaskKind.CODE)
    assert models and all(isinstance(m, str) for m in models)
    # coding model is preferred for code tasks
    assert any("compound" in m or "qwen" in m or "gpt-oss" in m for m in models)
