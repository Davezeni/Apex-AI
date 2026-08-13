"""Web search tools.

Default backend is DuckDuckGo (free, keyless). Tavily (keyed) is available as
a higher-quality alternative. NOTE: DuckDuckGo's HTML markup can change, so
this backend is best-effort and should be smoke-tested against the live page.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

import httpx

from .base import Tool, ToolContext, ToolResult


class SearchBackend(Protocol):
    async def search(self, query: str, max_results: int) -> list[dict[str, str]]: ...


class DuckDuckGoBackend:
    """Scrapes DuckDuckGo's HTML results page (no API key required)."""

    _URL = "https://html.duckduckgo.com/html/"
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        async with httpx.AsyncClient(headers=self._HEADERS, timeout=15.0) as client:
            resp = await client.post(self._URL, data={"q": query})
            resp.raise_for_status()
        return self._parse(resp.text, max_results)

    @staticmethod
    def _parse(html: str, max_results: int) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        # Each result: a title link followed by a snippet block.
        blocks = re.split(r'class="result results_links', html)[1:]
        for block in blocks:
            if len(results) >= max_results:
                break
            title_m = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block)
            snippet_m = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block)
            if not title_m:
                continue
            url = title_m.group(1)
            # Unwrap DuckDuckGo redirect URLs.
            uddg = re.search(r"uddg=([^&]+)", url)
            if uddg:
                from urllib.parse import unquote

                url = unquote(uddg.group(1))
            title = re.sub(r"<[^>]+>", "", title_m.group(2)).strip()
            snippet = (
                re.sub(r"<[^>]+>", "", snippet_m.group(1)).strip()
                if snippet_m
                else ""
            )
            results.append({"title": title, "url": url, "snippet": snippet})
        return results


class TavilyBackend:
    """Higher-quality search via Tavily (requires an API key)."""

    _URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                self._URL,
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in data.get("results", [])
        ]


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web and return titles, URLs, and snippets. "
        "Use to find current information or facts beyond your knowledge."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "description": "1-10 (default 5)"},
        },
        "required": ["query"],
    }

    def __init__(self, backend: SearchBackend) -> None:
        self._backend = backend

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(ok=False, summary="query must be a non-empty string")

        max_results = args.get("max_results", 5)
        if isinstance(max_results, (int, float)):
            max_results = max(1, min(10, int(max_results)))
        else:
            max_results = 5

        try:
            results = await self._backend.search(query, max_results)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"search failed: {exc}")

        if not results:
            return ToolResult(ok=True, summary="no results", content="(no results)")

        lines = [f"Search results for {query!r}:"]
        for r in results:
            lines.append(f"- {r['title']} ({r['url']})\n  {r['snippet']}")
        content = "\n".join(lines)
        return ToolResult(ok=True, summary=f"{len(results)} result(s)", content=content)
