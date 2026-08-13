"""Native Gemini provider adapter.

Uses Google's `google-genai` SDK against the *native* Gemini endpoint, which
is required for the newer `AQ.` authentication keys (OpenAI-compatible routes
reject them with 401). See docs/03-software-design.md §3.2.

The SDK call is synchronous, so it is executed in a thread via
`asyncio.to_thread` to avoid blocking the event loop. Streaming deltas are
currently deferred (on_delta is ignored); see NOTE below.
"""

from __future__ import annotations

import asyncio
import json

from google import genai
from google.genai import types

from .base import DeltaCallback, ProviderAdapter, ProviderError, RateLimitError
from ..schema import GenerateRequest, GenerateResponse, Message, ToolCall

_ROLE_MAP = {
    "system": "user",  # Gemini has no system role; see _system_instruction below
    "user": "user",
    "assistant": "model",
    "tool": "user",
}


class GeminiAdapter(ProviderAdapter):
    """Adapter for Google Gemini via the native google-genai SDK."""

    name = "gemini"

    def __init__(self, api_key: str | None, default_model: str) -> None:
        if not api_key:
            raise ProviderError("Gemini adapter requires an API key")
        self._client = genai.Client(api_key=api_key)
        self.default_model = default_model

    async def generate(
        self,
        req: GenerateRequest,
        on_delta: DeltaCallback = None,
    ) -> GenerateResponse:
        # NOTE: streaming is deferred; on_delta is intentionally unused until
        # the async streaming API is verified against the installed SDK version.
        del on_delta

        contents = self._to_contents(req)
        config = types.GenerateContentConfig(
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
            tools=self._to_tools(req) if req.tools else None,
            system_instruction=self._system_instruction(req),
        )

        try:
            result = await asyncio.to_thread(
                self._client.models.generate_content,
                model=req.model or self.default_model,
                contents=contents,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 — SDK raises various types
            raise ProviderError(f"gemini error: {exc}") from exc

        return self._parse_result(result)

    def _system_instruction(self, req: GenerateRequest) -> str | None:
        parts = [m.content for m in req.messages if m.role == "system" and m.content]
        return "\n\n".join(parts) if parts else None

    def _to_contents(self, req: GenerateRequest) -> list[types.Content]:
        """Map normalized messages to Gemini Content objects."""
        contents: list[types.Content] = []
        for m in req.messages:
            if m.role == "system":
                continue  # handled via system_instruction

            if m.role == "tool":
                # A tool result maps to a user turn with a function_response part.
                part = types.Part.from_function_response(
                    name=m.name or "tool",
                    response={"result": m.content or ""},
                )
                contents.append(types.Content(role="user", parts=[part]))
                continue

            if m.role == "assistant" and m.tool_calls:
                parts = [
                    types.Part.from_function_call(
                        name=tc.name, args=tc.arguments
                    )
                    for tc in m.tool_calls
                ]
                contents.append(types.Content(role="model", parts=parts))
                continue

            if m.content:
                contents.append(
                    types.Content(role=_ROLE_MAP[m.role], parts=[types.Part(text=m.content)])
                )
        return contents

    @staticmethod
    def _to_tools(req: GenerateRequest) -> list[types.Tool]:
        declarations = [
            types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=types.Schema.model_validate(t.parameters),
            )
            for t in req.tools
        ]
        return [types.Tool(function_declarations=declarations)]

    @staticmethod
    def _parse_result(result) -> GenerateResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for candidate in (result.candidates or []):
            for part in (candidate.content.parts if candidate.content else []):
                if part.text:
                    text_parts.append(part.text)
                if part.function_call:
                    fc = part.function_call
                    args = fc.args if isinstance(fc.args, dict) else {}
                    tool_calls.append(
                        ToolCall(id=fc.id or fc.name, name=fc.name, arguments=args)
                    )

        return GenerateResponse(
            text="".join(text_parts) or None,
            tool_calls=tool_calls,
        )
