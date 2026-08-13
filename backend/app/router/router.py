"""Model router: round-robin + failover + cooldown across a configured pool.

The router is the mechanism that defeats free-tier rate limits. It cycles
through the configured pool, fails over on errors, marks rate-limited models
with a cooldown, and wraps around so the pool never hard-fails as long as one
model (typically local Ollama) is available.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .providers.base import (
    DeltaCallback,
    ProviderAdapter,
    ProviderError,
    RateLimitError,
)
from .schema import GenerateRequest, GenerateResponse


@dataclass
class PoolEntry:
    """Runtime pool entry: config data + mutable failure/cooldown state."""

    provider: str
    model: str
    priority: int = 1
    cooldown_until: float = 0.0
    consecutive_failures: int = 0


class AllModelsExhausted(ProviderError):
    """Every model in the pool failed or is cooling down."""


class ModelRouter:
    """Routes generation requests across a pool with failover and cooldown."""

    def __init__(
        self,
        adapters: dict[str, ProviderAdapter],
        pool: list[PoolEntry],
        *,
        cooldown_seconds: int = 60,
        strategy: str = "round_robin",
    ) -> None:
        if not pool:
            raise ValueError("pool must not be empty")
        if strategy not in ("round_robin", "priority_first"):
            raise ValueError(f"unknown strategy: {strategy!r}")
        self._adapters = adapters
        self._pool = pool
        self._cooldown = cooldown_seconds
        self._strategy = strategy
        self._cursor = 0

    def _available(self, now: float) -> list[PoolEntry]:
        return [e for e in self._pool if e.cooldown_until <= now]

    def _ordered(self, available: list[PoolEntry]) -> list[PoolEntry]:
        # Stable: priority first, then original pool order.
        index = {id(e): i for i, e in enumerate(self._pool)}
        return sorted(available, key=lambda e: (e.priority, index[id(e)]))

    async def generate(
        self,
        req: GenerateRequest,
        on_delta: DeltaCallback = None,
    ) -> GenerateResponse:
        now = time.monotonic()
        ordered = self._ordered(self._available(now))
        if not ordered:
            raise AllModelsExhausted("all models are in cooldown")

        errors: list[str] = []
        attempts = len(ordered)

        for i in range(attempts):
            if self._strategy == "round_robin":
                entry = ordered[self._cursor % attempts]
                self._cursor += 1
            else:  # priority_first
                entry = ordered[i]

            adapter = self._adapters.get(entry.provider)
            if adapter is None:
                errors.append(f"{entry.provider}: no adapter registered")
                continue

            try:
                req.model = entry.model
                return await adapter.generate(req, on_delta=on_delta)
            except RateLimitError as exc:
                entry.cooldown_until = time.monotonic() + self._cooldown
                entry.consecutive_failures += 1
                errors.append(str(exc))
            except ProviderError as exc:
                entry.consecutive_failures += 1
                errors.append(str(exc))

        raise AllModelsExhausted("; ".join(errors))
