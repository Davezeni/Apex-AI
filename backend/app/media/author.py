"""Document authoring: generate engineering documents from templates.

Markdown is the authoring format; each document type is a template with
sections filled from the provided details. Output is Markdown (rendered to
.docx etc. by the existing conversion pipeline when needed).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEMPLATES: dict[str, str] = {
    "sad": """# {title} — System Architecture Document (SAD)

**Version:** 1.0
**Date:** {date}

## 1. Introduction
{overview}

## 2. Architectural Goals
{goals}

## 3. System Context
{context}

## 4. Components
{components}

## 5. Technology Stack
{stack}

## 6. Data Flow
{dataflow}
""",
    "sdd": """# {title} — Software Design Document (SDD)

**Version:** 1.0
**Date:** {date}

## 1. Module Structure
{modules}

## 2. Key Interfaces
{interfaces}

## 3. Data Models
{models}

## 4. Algorithms & Logic
{algorithms}
""",
    "prd": """# {title} — Product Requirements Document (PRD)

**Version:** 1.0
**Date:** {date}

## 1. Problem Statement
{overview}

## 2. Goals & Non-Goals
{goals}

## 3. Functional Requirements
{components}

## 4. Non-Functional Requirements
{stack}
""",
    "readme": """# {title}

{overview}

## Features
{goals}

## Getting Started
```bash
{stack}
```

## Structure
{components}
""",
}

_FIELD_KEYS = ("overview", "goals", "context", "components", "stack", "dataflow",
               "modules", "interfaces", "models", "algorithms")


def generate_document(
    doc_type: str,
    title: str,
    details: dict[str, Any],
    date: str = "",
) -> str:
    template = TEMPLATES.get(doc_type.lower())
    if template is None:
        raise ValueError(f"unknown doc_type {doc_type!r} (choose {list(TEMPLATES)})")

    from datetime import date as _date

    date = date or _date.today().isoformat()

    fields: dict[str, str] = {"title": title, "date": date}
    for key in _FIELD_KEYS:
        value = details.get(key, "")
        if isinstance(value, (list, tuple)):
            value = "\n".join(f"- {v}" for v in value)
        fields[key] = str(value or "")

    return template.format(**fields)


def write_document(
    doc_type: str,
    title: str,
    details: dict[str, Any],
    out_path: Path,
) -> Path:
    out_path.write_text(generate_document(doc_type, title, details), encoding="utf-8")
    return out_path
