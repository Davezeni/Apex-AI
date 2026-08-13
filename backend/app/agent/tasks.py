"""Task classification and personas.

Apex AI adapts its behaviour to the *kind* of request:
- chat → warm, concise, conversational (human-like)
- code / math / design / data → rigorous, structured, expert (AI-like)

The classifier is keyword/heuristic based so it costs zero extra model calls
(no latency). It only influences *which persona prompt and which models are
preferred* — it never blocks a request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskKind(str, Enum):
    CHAT = "chat"
    CODE = "code"
    MATH = "math"
    DESIGN = "design"
    DATA = "data"
    GENERAL = "general"


@dataclass(frozen=True)
class Classified:
    kind: TaskKind
    confidence: float  # 0..1


# --- Personas -------------------------------------------------------------

CHAT_PERSONA = (
    "You are Apex AI, a friendly, knowledgeable assistant. Be warm, natural, "
    "and genuinely conversational — like a helpful expert talking with a "
    "colleague, not a machine. Use plain language, short sentences, and a "
    "human tone. Answer directly and concisely; don't over-explain or list "
    "steps unless the user asks. Feel free to be personable, ask a clarifying "
    "question when it's genuinely helpful, and match the user's energy. When "
    "you don't know something, say so honestly. Remember the earlier "
    "conversation and refer back to it naturally."
)

ENGINEER_PERSONA = (
    "You are Apex AI, a senior software engineer and architect embedded in a "
    "self-hosted builder. You build real, working software — not snippets — "
    "and solve technical problems with rigour and precision.\n\n"
    "For code, math, and technical work:\n"
    "- PLAN first: state the approach in one or two lines.\n"
    "- For a project: SCAFFOLD a proper structure (create_structure), then "
    "WRITE each file completely (write_file), then RUN/VERIFY (run_command "
    "when a sandbox is available), then EXPLAIN.\n"
    "- Write correct, idiomatic, runnable code. Prefer clarity and correctness "
    "over cleverness. Include necessary imports, config, and a README.\n"
    "- For math: show your reasoning step by step and arrive at a clear answer.\n"
    "- For design: be specific — give concrete, actionable design decisions "
    "(layout, hierarchy, colour, typography) rather than vague advice.\n"
    "- Choose the most appropriate language for the task and say why.\n\n"
    "Memory: use the conversation history; build on earlier decisions, don't "
    "re-ask them.\n\n"
    "Honesty: end with (1) DONE, (2) NOT DONE / untested, (3) next steps. "
    "Never imply unverified work succeeded."
)

DATA_PERSONA = ENGINEER_PERSONA  # data work uses the same rigorous style.

PERSONAS: dict[TaskKind, str] = {
    TaskKind.CHAT: CHAT_PERSONA,
    TaskKind.CODE: ENGINEER_PERSONA,
    TaskKind.MATH: ENGINEER_PERSONA,
    TaskKind.DESIGN: ENGINEER_PERSONA,
    TaskKind.DATA: DATA_PERSONA,
    TaskKind.GENERAL: ENGINEER_PERSONA,
}


# --- Classification -------------------------------------------------------

# Lowercase keyword lists per task. A match strongly indicates the task kind.
_KEYWORDS: dict[TaskKind, tuple[str, ...]] = {
    TaskKind.CODE: (
        "code", "coding", "function", "api", "app", "website", "script",
        "program", "python", "javascript", "typescript", "react", "node",
        "golang", "go lang", "rust", "java", "sql", "backend", "frontend",
        "bug", "debug", "error", "framework", "class", "import", "docker",
        "deploy", "build a", "create a", "scaffold", "library", "package",
    ),
    TaskKind.MATH: (
        "math", "calculate", "equation", "solve", "algebra", "calculus",
        "derivative", "integral", "geometry", "theorem", "proof", "sum",
        "multiply", "divide", "percentage", "formula", "statistic", "probability",
        "fibonacci", "prime", "matrix", "vector",
    ),
    TaskKind.DESIGN: (
        "design", "ui", "ux", "color", "colour", "palette", "layout", "logo",
        "font", "typography", "brand", "style", "mockup", "wireframe",
        "graphic", "illustration", "aesthetic", "banner", "poster",
    ),
    TaskKind.DATA: (
        "data", "csv", "excel", "spreadsheet", "chart", "graph", "analysis",
        "analyze", "visualize", "visualise", "table", "dataset", "report",
        "pandas", "chart", "plot",
    ),
}

_CHAT_HINTS = (
    "hi", "hello", "hey", "how are you", "what's up", "whats up", "thanks",
    "thank you", "good morning", "good evening", "good afternoon", "talk",
    "chat", "your name", "who are you", "what can you do", "how do you",
    "are you", "can we talk", "nice", "cool", "awesome", "great", "okay",
    "ok thanks", "lol", "haha", "tell me about yourself", "what do you think",
)

_QUESTION_OPENERS = (
    "what", "how", "why", "when", "where", "who", "which", "can", "could",
    "would", "should", "do", "does", "is", "are", "was", "were",
)


def _match_count(lowered: str, keywords: tuple[str, ...]) -> int:
    """Count keyword hits using word boundaries for single-word keywords
    (so 'api' doesn't match inside 'capital') and substring for phrases."""
    score = 0
    for kw in keywords:
        if " " in kw:
            if kw in lowered:
                score += 1
        elif re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", lowered):
            score += 1
    return score


def classify(text: str) -> Classified:
    """Classify a user message into a task kind (fast, heuristic)."""
    lowered = text.lower().strip()
    words = lowered.split()

    # Casual openers / short greetings → chat.
    if len(words) <= 4:
        for hint in _CHAT_HINTS:
            if lowered == hint or lowered.startswith(hint):
                return Classified(TaskKind.CHAT, 0.9)

    scores: dict[TaskKind, int] = {}
    for kind, keywords in _KEYWORDS.items():
        scores[kind] = _match_count(lowered, keywords)

    best_kind = max(scores, key=lambda k: scores[k])
    best_score = scores[best_kind]

    # No strong technical signal → likely chat or general. Use chat hints and
    # question phrasing to prefer a conversational response.
    if best_score == 0:
        for hint in _CHAT_HINTS:
            if hint in lowered:
                return Classified(TaskKind.CHAT, 0.75)
        first = words[0] if words else ""
        if first in _QUESTION_OPENERS and len(words) <= 12:
            return Classified(TaskKind.CHAT, 0.5)
        return Classified(TaskKind.GENERAL, 0.3)

    total = sum(scores.values()) or 1
    confidence = min(0.95, 0.5 + best_score / (total + best_score) * 0.5)
    return Classified(best_kind, confidence)


# --- Model preference per task -------------------------------------------
# A task prefers models that are strong at that kind of work; the router uses
# these to bias selection (but still falls back across the whole pool).

TASK_MODEL_PREFERENCE: dict[TaskKind, list[str]] = {
    TaskKind.CODE: ["groq/compound", "qwen/qwen3.6-27b", "openai/gpt-oss-120b"],
    TaskKind.MATH: ["openai/gpt-oss-120b", "qwen/qwen3.6-27b"],
    TaskKind.DESIGN: ["gemini-3.6-flash", "llama-3.3-70b-versatile"],
    TaskKind.DATA: ["qwen/qwen3.6-27b", "llama-3.3-70b-versatile"],
    TaskKind.CHAT: ["llama-3.3-70b-versatile", "gemini-3.6-flash", "llama-3.1-8b-instant"],
    TaskKind.GENERAL: ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"],
}


def persona_for(kind: TaskKind) -> str:
    return PERSONAS[kind]


def preferred_models(kind: TaskKind) -> list[str]:
    return TASK_MODEL_PREFERENCE.get(kind, [])


__all__ = [
    "TaskKind",
    "Classified",
    "classify",
    "persona_for",
    "preferred_models",
]
