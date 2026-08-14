"""OpenAI-compatible provider adapter (Groq, Ollama).

Groq and Ollama both expose an OpenAI-style `/chat/completions` endpoint,
so a single adapter serves both via configuration. Supports native tool
calling and streaming token deltas.
"""

from __future__ import annotations

import json

import httpx

from .base import DeltaCallback, ProviderAdapter, ProviderError, RateLimitError
from ..schema import GenerateRequest, GenerateResponse, Message, ToolCall

_ROLE_MAP = {
    "system": "system",
    "user": "user",
    "assistant": "assistant",
    "tool": "tool",
}


class OpenAICompatAdapter(ProviderAdapter):
    """Adapter for any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str | None,
        default_model: str,
        timeout: float = 120.0,
    ) -> None:
        self.name = name
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )
        self.default_model = default_model

    async def generate(
        self,
        req: GenerateRequest,
        on_delta: DeltaCallback = None,
    ) -> GenerateResponse:
        model = req.model or self.default_model
        payload: dict = {
            "model": model,
            "messages": [self._to_wire(m) for m in req.messages],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": on_delta is not None,
        }
        if req.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in req.tools
            ]
            payload["tool_choice"] = "auto"

        try:
            if on_delta is not None:
                return await self._generate_streaming(payload, on_delta)
            resp = await self._client.post("/chat/completions", json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name} transport error: {exc}") from exc

        if resp.status_code == 429:
            raise RateLimitError(f"{self.name} rate limited (HTTP 429)")
        if resp.status_code != 200:
            raise ProviderError(
                f"{self.name} HTTP {resp.status_code}: {resp.text[:500]}"
            )

        return self._parse_message(resp.json()["choices"][0]["message"])

    async def _generate_streaming(
        self, payload: dict, on_delta: DeltaCallback
    ) -> GenerateResponse:
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls: dict[int, dict] = {}

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
                if resp.status_code == 429:
                    raise RateLimitError(f"{self.name} rate limited (HTTP 429)")
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise ProviderError(
                        f"{self.name} HTTP {resp.status_code}: {body[:500]!r}"
                    )

                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    choices = chunk.get("choices")
                    if not choices:
                        continue  # usage/error chunk with no choices
                    delta = choices[0].get("delta") or {}

                    if delta.get("reasoning"):
                        reasoning_parts.append(delta["reasoning"])

                    if delta.get("content"):
                        text_parts.append(delta["content"])
                        await on_delta(delta["content"])

                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        slot = tool_calls.setdefault(idx, {"id": "", "name": "", "args": ""})
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        if tc.get("function", {}).get("name"):
                            slot["name"] = tc["function"]["name"]
                        if tc.get("function", {}).get("arguments"):
                            slot["args"] += tc["function"]["arguments"]
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name} stream error: {exc}") from exc

        calls = []
        for slot in sorted(tool_calls.values(), key=lambda s: list(tool_calls.values()).index(s)):
            try:
                args = json.loads(slot["args"]) if slot["args"] else {}
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(id=slot["id"], name=slot["name"], arguments=args))

        text = "".join(text_parts) or None
        reasoning = "".join(reasoning_parts) or None
        return GenerateResponse(text=text, tool_calls=calls, reasoning=reasoning)

    @staticmethod
    def _parse_message(message: dict) -> GenerateResponse:
        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args)
            )
        reasoning = message.get("reasoning") or None
        content = message.get("content")
        # Some reasoning models return only `reasoning` and empty content when
        # they think; treat trailing reasoning as the answer if no content.
        return GenerateResponse(
            text=content or None,
            tool_calls=tool_calls,
            reasoning=reasoning,
        )

    @staticmethod
    def _to_wire(m: Message) -> dict:
        msg: dict = {"role": _ROLE_MAP[m.role]}
        # Tool messages MUST always carry a content field (even empty), and
        # assistant/user text goes into content too.
        if m.role == "tool":
            msg["content"] = m.content if m.content is not None else ""
        elif m.content:
            msg["content"] = m.content
        if m.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in m.tool_calls
            ]
        if m.tool_call_id:
            msg["tool_call_id"] = m.tool_call_id
        if m.name:
            msg["name"] = m.name
        return msg

    async def close(self) -> None:
        await self._client.aclose()
