"""Native Gemini provider adapter (REST via httpx).

Uses the *native* `generativelanguage.googleapis.com` endpoint, which is
required for the newer `AQ.` authentication keys (OpenAI-compatible routes
reject them with 401). Verified live against the `gemini-3.5-flash` model.

No third-party SDK dependency: request/response mapping is explicit, including
native function calling (`functionDeclarations` → `functionCall` /
`functionResponse` parts).
"""

from __future__ import annotations

import json

import httpx

from .base import DeltaCallback, ProviderAdapter, ProviderError, RateLimitError
from ..schema import GenerateRequest, GenerateResponse, Message, ToolCall

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiAdapter(ProviderAdapter):
    name = "gemini"

    def __init__(self, api_key: str, default_model: str, timeout: float = 120.0) -> None:
        if not api_key:
            raise ProviderError("Gemini adapter requires an API key")
        self._key = api_key
        self.default_model = default_model
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(
        self,
        req: GenerateRequest,
        on_delta: DeltaCallback = None,
    ) -> GenerateResponse:
        # NOTE: streaming (on_delta) is not used; Gemini non-stream returns the
        # full text, which the agent emits once.
        del on_delta

        model = req.model or self.default_model
        url = ENDPOINT.format(model=model) + f"?key={self._key}"

        payload: dict = {
            "contents": self._to_contents(req),
            "generationConfig": {
                "temperature": req.temperature,
                "maxOutputTokens": req.max_tokens,
            },
        }
        system = self._system_instruction(req)
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        tools = self._to_tools(req)
        if tools:
            payload["tools"] = tools

        try:
            resp = await self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"gemini transport error: {exc}") from exc

        if resp.status_code == 429:
            raise RateLimitError("gemini rate limited (HTTP 429)")
        if resp.status_code >= 400:
            raise ProviderError(f"gemini HTTP {resp.status_code}: {resp.text[:500]}")

        return self._parse_result(resp.json())

    def _system_instruction(self, req: GenerateRequest) -> str | None:
        parts = [m.content for m in req.messages if m.role == "system" and m.content]
        return "\n\n".join(parts) if parts else None

    def _to_contents(self, req: GenerateRequest) -> list[dict]:
        contents: list[dict] = []
        for m in req.messages:
            if m.role == "system":
                continue

            if m.role == "tool":
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": m.name or "tool",
                            "response": {"result": m.content or ""},
                        }
                    }],
                })
                continue

            if m.role == "assistant" and m.tool_calls:
                parts = []
                for tc in m.tool_calls:
                    fc: dict = {"name": tc.name, "args": tc.arguments}
                    if tc.thought_signature:
                        fc["thought_signature"] = tc.thought_signature
                    parts.append({"functionCall": fc})
                contents.append({"role": "model", "parts": parts})
                continue

            if m.content:
                contents.append({"role": "user" if m.role == "user" else "model",
                                 "parts": [{"text": m.content}]})
        return contents

    @staticmethod
    def _to_tools(req: GenerateRequest) -> list[dict] | None:
        if not req.tools:
            return None
        return [{
            "functionDeclarations": [
                {"name": t.name, "description": t.description, "parameters": t.parameters}
                for t in req.tools
            ]
        }]

    @staticmethod
    def _parse_result(data: dict) -> GenerateResponse:
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for candidate in data.get("candidates", []):
            for part in (candidate.get("content") or {}).get("parts", []):
                if "text" in part:
                    # Gemini marks thinking parts with thought=True.
                    if part.get("thought"):
                        reasoning_parts.append(part["text"])
                    else:
                        text_parts.append(part["text"])
                if "functionCall" in part:
                    fc = part["functionCall"]
                    args = fc.get("args") if isinstance(fc.get("args"), dict) else {}
                    tool_calls.append(
                        ToolCall(
                            id=fc.get("name", ""),
                            name=fc["name"],
                            arguments=args,
                            thought_signature=fc.get("thought_signature"),
                        )
                    )

        return GenerateResponse(
            text="".join(text_parts) or None,
            tool_calls=tool_calls,
            reasoning="".join(reasoning_parts) or None,
        )
