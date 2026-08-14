"""Dependency assembly: builds the router, tools, agent, and collaborators.

Only provider adapters for which we have credentials (or a local endpoint)
are registered, so the app runs on local Ollama alone with zero keys. The
sandbox, GitHub client, and knowledge base are optional and wired when their
prerequisites (Docker, a token) are present.
"""

from __future__ import annotations

from .config import Settings, load_settings
from .integrations.github import GitHubClient
from .media.image_gen import ImageGenerator
from .media.vision import VisionClient
from .memory.rag import HashEmbedder, KnowledgeBase
from .memory.store import Store
from .router.providers.base import ProviderAdapter
from .router.providers.gemini import GeminiAdapter
from .router.providers.openai_compat import OpenAICompatAdapter
from .router.router import ModelRouter, PoolEntry
from .sandbox.base import Sandbox
from .sandbox.codespaces import CodespacesSandbox
from .sandbox.docker import DockerSandbox
from .tools.author import GenerateDocumentTool
from .tools.charts import GenerateChartTool
from .tools.document import ConvertFileTool, ParseDocumentTool
from .tools.filesystem import (
    CreateStructureTool,
    DeleteFileTool,
    EditFileTool,
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
)
from .tools.github import (
    GitHubCreateRepoTool,
    GitCloneTool,
    GitCommitTool,
    GitPullTool,
    GitPushTool,
)
from .tools.image_gen import GenerateImageTool
from .tools.knowledge import KnowledgeAddTool, KnowledgeQueryTool
from .tools.preview import PreviewTool
from .tools.registry import ToolContext, ToolRegistry
from .tools.sandbox import RunCommandTool, SandboxStatusTool
from .tools.vision import DescribeImageTool, OcrImageTool
from .tools.web_search import DuckDuckGoBackend, TavilyBackend, WebSearchTool
from .tools.workspace import WorkspaceProtectTool

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
            default_model="gemini-3.5-flash",
        )
    # Ollama is local and needs no key; register only when enabled (skipped on
    # hosts like Render where no local server runs).
    if settings.enable_ollama:
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


def build_store(settings: Settings) -> Store:
    """Build the conversation/knowledge store.

    Degrades gracefully: if Supabase is requested but its credentials are
    missing, fall back to local SQLite with a warning rather than crashing.
    """
    import logging

    logger = logging.getLogger("apex.store")

    if settings.store_backend == "supabase":
        if settings.supabase_url and settings.supabase_service_role_key:
            from .memory.supabase_store import SupabaseStore

            return SupabaseStore(settings.supabase_url, settings.supabase_service_role_key)
        logger.warning(
            "STORE_BACKEND=supabase but SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY "
            "are not set — falling back to local SQLite (memory will NOT "
            "survive redeploys until you set those env vars)."
        )
    return Store(settings.workspace_root.parent / "apex.sqlite3")


def build_knowledge(settings: Settings) -> KnowledgeBase:
    return KnowledgeBase(build_store(settings), HashEmbedder())


def build_github(settings: Settings) -> GitHubClient | None:
    return GitHubClient(settings.github_token) if settings.github_token else None


def build_mcp_manager(settings: Settings) -> "MCPManager":
    from .mcp.client import MCPServerConfig, MCPManager

    servers = [
        MCPServerConfig(
            name=s.get("name", f"server{i}"),
            command=s["command"],
            args=s.get("args", []),
            env=s.get("env", {}),
        )
        for i, s in enumerate(settings.mcp_servers)
        if isinstance(s, dict) and s.get("command")
    ]
    return MCPManager(servers)


def build_vision(settings: Settings) -> VisionClient | None:
    return VisionClient(settings.gemini_api_key) if settings.gemini_api_key else None


def build_image_gen(settings: Settings) -> ImageGenerator:
    return ImageGenerator()


def build_sandbox(settings: Settings) -> Sandbox | None:
    """Select the sandbox backend by configuration.

    - "docker": local container mounting the workspace (recommended default).
    - "codespaces": GitHub Codespaces via the `gh` CLI; requires an active
      Codespace and `codespace_name` set.
    """
    if settings.sandbox_backend == "codespaces":
        if not settings.codespace_name:
            return None
        return CodespacesSandbox(codespace_name=settings.codespace_name)
    return DockerSandbox(container="apex-sandbox")


def build_tools(
    settings: Settings,
    knowledge: KnowledgeBase | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in (
        WriteFileTool(),
        ReadFileTool(),
        ListFilesTool(),
        EditFileTool(),
        DeleteFileTool(),
        CreateStructureTool(),
        ParseDocumentTool(),
        ConvertFileTool(),
        RunCommandTool(),
        SandboxStatusTool(),
        GitHubCreateRepoTool(),
        GitCloneTool(),
        GitCommitTool(),
        GitPushTool(),
        GitPullTool(),
        KnowledgeAddTool(),
        KnowledgeQueryTool(),
        WorkspaceProtectTool(),
        GenerateChartTool(),
        GenerateDocumentTool(),
        PreviewTool(),
    ):
        registry.register(tool)

    # Vision tools require a Gemini key; image generation is keyless.
    vision = build_vision(settings)
    if vision is not None:
        registry.register(DescribeImageTool(vision))
        registry.register(OcrImageTool(vision))
    registry.register(GenerateImageTool(ImageGenerator()))

    backend = (
        TavilyBackend(settings.tavily_api_key)
        if settings.tavily_api_key
        else DuckDuckGoBackend()
    )
    registry.register(WebSearchTool(backend))
    return registry


def build_tool_context(
    settings: Settings,
    github: GitHubClient | None = None,
    sandbox: Sandbox | None = None,
    knowledge: KnowledgeBase | None = None,
) -> ToolContext:
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        workspace_root=settings.workspace_root,
        github=github,
        sandbox=sandbox,
        knowledge=knowledge,
    )
