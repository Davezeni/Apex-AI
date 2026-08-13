"""Vision via Gemini's native endpoint (works with the AQ. auth key).

Uses the same `generativelanguage.googleapis.com` REST endpoint verified for
text generation, but with inline image data. Two capabilities:
- describe: a caption/summary of the image.
- extract_text: OCR-style extraction of any text in the image.
"""

from __future__ import annotations

import base64

import httpx

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class VisionClient:
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash", timeout: float = 120.0) -> None:
        if not api_key:
            raise ValueError("VisionClient requires an API key")
        self._key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _analyze(self, image_bytes: bytes, mime: str, instruction: str) -> str:
        url = ENDPOINT.format(model=self._model) + f"?key={self._key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": instruction},
                        {"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}},
                    ]
                }
            ]
        }
        resp = await self._client.post(url, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"vision HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        text_parts = []
        for candidate in data.get("candidates", []):
            for part in (candidate.get("content") or {}).get("parts", []):
                if "text" in part:
                    text_parts.append(part["text"])
        return "".join(text_parts).strip()

    async def describe(self, image_bytes: bytes, mime: str) -> str:
        return await self._analyze(
            image_bytes, mime,
            "Describe this image in detail: what it shows, its composition, and any notable elements.",
        )

    async def extract_text(self, image_bytes: bytes, mime: str) -> str:
        return await self._analyze(
            image_bytes, mime,
            "Extract ALL text visible in this image, verbatim, preserving lines. If there is no text, say 'NO_TEXT'.",
        )

    async def close(self) -> None:
        await self._client.aclose()


def mime_for(filename: str) -> str:
    for ext, mime in _IMAGE_MIME.items():
        if filename.lower().endswith(ext):
            return mime
    return "image/png"
