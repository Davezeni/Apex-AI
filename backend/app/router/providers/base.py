"""Provider adapter interface and error hierarchy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from ..schema import GenerateRequest, GenerateResponse

# on_delta streams assistant text tokens as they arrive (None when the
# provider does not support streaming).
DeltaCallback = Callable[[str], Awaitable[None]] | None


class ProviderError(Exception):
    """A provider failed; the router may fail over to the next model."""


class RateLimitError(ProviderError):
    """Provider rate limit hit; triggers cooldown + failover."""


class ProviderAdapter(ABC):
    """Interface every model provider must implement."""

    name: str

    @abstractmethod
    async def generate(
        self,
        req: GenerateRequest,
        on_delta: DeltaCallback = None,
    ) -> GenerateResponse:
        """Produce a response (text and/or tool calls) from a request."""
        raise NotImplementedError
