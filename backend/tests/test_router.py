"""Tests for the model router's failover, round-robin, and cooldown behavior.

Uses a fake adapter so no network is required.
"""

from __future__ import annotations

import pytest

from app.router.providers.base import ProviderAdapter, ProviderError, RateLimitError
from app.router.router import AllModelsExhausted, ModelRouter, PoolEntry
from app.router.schema import GenerateRequest, GenerateResponse, Message


class FakeAdapter(ProviderAdapter):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[GenerateRequest] = []
        self.responses: list = []  # GenerateResponse or Exception
        self._index = 0

    def queue(self, *responses) -> None:
        self.responses = list(responses)
        self._index = 0

    async def generate(self, req, on_delta=None):
        self.calls.append(req)
        if self._index >= len(self.responses):
            raise ProviderError(f"{self.name}: no more queued responses")
        item = self.responses[self._index]
        self._index += 1
        if isinstance(item, Exception):
            raise item
        return item


def make_request() -> GenerateRequest:
    return GenerateRequest(messages=[Message(role="user", content="hi")])


def ok(text: str) -> GenerateResponse:
    return GenerateResponse(text=text)


@pytest.mark.asyncio
async def test_success_returns_response():
    a = FakeAdapter("a")
    a.queue(ok("hello"))
    router = ModelRouter({"a": a}, [PoolEntry("a", "m1")])

    resp = await router.generate(make_request())
    assert resp.text == "hello"


@pytest.mark.asyncio
async def test_failover_on_rate_limit():
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    a.queue(RateLimitError("a limited"))
    b.queue(ok("from b"))
    router = ModelRouter(
        {"a": a, "b": b},
        [PoolEntry("a", "m1", priority=1), PoolEntry("b", "m2", priority=2)],
    )

    resp = await router.generate(make_request())
    assert resp.text == "from b"
    # 'a' should now be cooling down.
    assert a.calls == [make_request()] or len(a.calls) == 1


@pytest.mark.asyncio
async def test_round_robin_cycles_models():
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    a.queue(ok("a1"), ok("a2"))
    b.queue(ok("b1"), ok("b2"))
    router = ModelRouter(
        {"a": a, "b": b},
        [PoolEntry("a", "m1", priority=1), PoolEntry("b", "m2", priority=1)],
        strategy="round_robin",
    )

    models = []
    for _ in range(4):
        resp = await router.generate(make_request())
        models.append(resp.text)

    # With equal priority and round-robin, the first two calls hit a then b,
    # then wrap: a, b, a, b.
    assert models == ["a1", "b1", "a2", "b2"]


@pytest.mark.asyncio
async def test_priority_first_always_tries_best():
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    a.queue(ok("a1"), ok("a2"))
    b.queue(ok("b1"))
    router = ModelRouter(
        {"a": a, "b": b},
        [PoolEntry("a", "m1", priority=1), PoolEntry("b", "m2", priority=2)],
        strategy="priority_first",
    )

    assert (await router.generate(make_request())).text == "a1"
    assert (await router.generate(make_request())).text == "a2"
    # 'b' was never needed.
    assert len(b.calls) == 0


@pytest.mark.asyncio
async def test_cooldown_blocks_model_until_expiry():
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    a.queue(RateLimitError("limited"))
    b.queue(ok("b"))
    router = ModelRouter(
        {"a": a, "b": b},
        [PoolEntry("a", "m1", priority=1), PoolEntry("b", "m2", priority=2)],
        cooldown_seconds=60,
    )
    await router.generate(make_request())  # a rate-limits, b answers

    # Immediately after, 'a' is in cooldown, so only 'b' is attempted.
    b.queue(ok("b2"))
    await router.generate(make_request())
    assert len(a.calls) == 1  # a was not retried


@pytest.mark.asyncio
async def test_all_exhausted_raises():
    a = FakeAdapter("a")
    a.queue(ProviderError("boom"))
    router = ModelRouter({"a": a}, [PoolEntry("a", "m1")])

    with pytest.raises(AllModelsExhausted):
        await router.generate(make_request())
