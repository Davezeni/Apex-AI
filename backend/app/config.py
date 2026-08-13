"""Application configuration.

Secrets are loaded from environment variables / a git-ignored `.env` file via
pydantic-settings. Non-secret tunables (notably the model pool and router
strategy) are loaded from an optional `config.yaml` at the project root.

Nothing secret is ever hardcoded or committed.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = ROOT_DIR / "config.yaml"

RouterStrategy = Literal["round_robin", "priority_first"]


class PoolEntry(BaseModel):
    """A single entry in the model routing pool."""

    provider: str
    model: str
    priority: int = 1

    @field_validator("priority")
    @classmethod
    def _priority_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("priority must be >= 1")
        return v


class Settings(BaseSettings):
    """Runtime settings. Secret values originate from env / .env only."""

    model_config = SettingsConfigDict(
        # Absolute path so the app finds .env regardless of CWD (repo root).
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Secrets (optional: the app runs on local Ollama with none) ---
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    tavily_api_key: str | None = None
    github_token: str | None = None

    # --- Local model ---
    ollama_base_url: str = "http://localhost:11434"

    # --- Agent / router tuning ---
    max_iterations: int = 12
    cooldown_seconds: int = 60
    request_timeout_seconds: float = 120.0
    strategy: RouterStrategy = "round_robin"

    # --- Workspace ---
    workspace_root: Path = ROOT_DIR / "workspace"

    # --- Model pool (overridable via config.yaml) ---
    pool: list[PoolEntry] = Field(
        default_factory=lambda: [
            PoolEntry(provider="groq", model="llama-3.3-70b-versatile", priority=1),
            PoolEntry(provider="gemini", model="gemini-3.5-flash", priority=2),
            PoolEntry(provider="ollama", model="qwen2.5:14b", priority=9),
        ]
    )


def _apply_config_file(settings: Settings) -> Settings:
    """Overlay non-secret tunables from config.yaml when present."""
    if not CONFIG_FILE.exists():
        return settings

    raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}

    models = raw.get("models") or {}
    if isinstance(models.get("pool"), list):
        settings.pool = [PoolEntry(**entry) for entry in models["pool"]]
    if "strategy" in models:
        settings.strategy = models["strategy"]
    for key in ("cooldown_seconds",):
        if key in models:
            setattr(settings, key, models[key])

    agent = raw.get("agent") or {}
    if "max_iterations" in agent:
        settings.max_iterations = agent["max_iterations"]

    return settings


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Return the (cached) application settings."""
    return _apply_config_file(Settings())
