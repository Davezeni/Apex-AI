"""Dependency assembly: builds the router, tools, and agent from settings.

Only provider adapters for which we have credentials (or a local endpoint)
are registered, so the app runs on local Ollama alone with zero keys.
"""

from __future__ import annotations

from .config import Settings, load_settings
from .router.providers.base import ProviderAdapter
from .router.providers.gemini import GeminiAdapter
from .router.providers.openai_compat import OpenAICompatAdapter
from .router.router import ModelRouter, PoolEntry
from .tools.filesystem import (
    CreateStructureTool,
    DeleteFileTool,
    EditFileTool,
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
)
from .tools.registry import ToolContext, ToolRegistry
from .tools.web_search import DuckDuckGoBackend, TavilyBackend, WebSearchTool

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def build_adapters(settings: Settings) -> dict[str, ProviderAdapter]:
    adapters: dict[str, ProviderAdapter] = {}

    if settings.groq_api_key:
        adapters["groq"] = OpenAICompatAdapter(
            name="groq",
            base_url=GROQ_BASE_URL,
            api_key=settings.groq_api_key,
            default_model="llama-3.3-70b-versatile",
            timeout=settings.request_timeout_seconds,
        )
    if settings.gemini_api_key:
        adapters["gemini"] = GeminiAdapter(
            api_key=settings.gemini_api_key,
            default_model="gemini-2.5-flash",
        )
    # Ollama is local and needs no key; always available.
    adapters["ollama"] = OpenAICompatAdapter(
        name="ollama",
        base_url=f"{settings.ollama_base_url}/v1",
        api_key=None,
        default_model="qwen2.5:14b",
        timeout=settings.request_timeout_seconds,
    )
    return adapters


def build_router(
    settings: Settings, adapters: dict[str, ProviderAdapter]
) -> ModelRouter:
    pool = [
        PoolEntry(provider=e.provider, model=e.model, priority=e.priority)
        for e in settings.pool
        if e.provider in adapters
    ]
    if not pool:
        raise RuntimeError("no usable model pool entries (add a key or run Ollama)")
    return ModelRouter(
        adapters,
        pool,
        cooldown_seconds=settings.cooldown_seconds,
        strategy=settings.strategy,
    )


def build_tools(settings: Settings) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in (
        WriteFileTool(),
        ReadFileTool(),
        ListFilesTool(),
        EditFileTool(),
        DeleteFileTool(),
        CreateStructureTool(),
    ):
        registry.register(tool)

    backend = (
        TavilyBackend(settings.tavily_api_key)
        if settings.tavily_api_key
        else DuckDuckGoBackend()
    )
    registry.register(WebSearchTool(backend))
    return registry


def build_tool_context(settings: Settings) -> ToolContext:
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    return ToolContext(workspace_root=settings.workspace_root)
