"""Image generation via Pollinations.ai (free, keyless)."""

from __future__ import annotations

from urllib.parse import quote

import httpx


class ImageGenerator:
    """Generates images from text prompts (no API key required)."""

    BASE = "https://image.pollinations.ai/prompt/"

    def __init__(self, timeout: float = 180.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
    ) -> bytes:
        url = f"{self.BASE}{quote(prompt)}?width={width}&height={height}&nologo=true"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.content

    async def close(self) -> None:
        await self._client.aclose()
