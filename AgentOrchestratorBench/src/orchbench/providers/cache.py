"""A content-addressed on-disk cache that wraps any provider.

Keyed on the semantic content of the request -- model, messages, tools,
temperature -- so re-running a sweep after a crash, or comparing orchestrators
that happen to issue identical prompts, costs nothing the second time. This is
the difference between a benchmark you can afford to iterate on and one you run
once and never touch again.

The ``task_id`` in request metadata is deliberately *excluded* from the key:
the cache keys on what was actually sent to the model, not on our bookkeeping.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from orchbench.providers.base import LLMProvider
from orchbench.types import LLMRequest, ModelResponse


def _key(request: LLMRequest) -> str:
    payload = {
        "model": request.model,
        "messages": request.messages,
        "tools": request.tools,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


class CachingProvider:
    """Wrap a provider with a read-through JSON file cache."""

    def __init__(self, inner: LLMProvider, cache_dir: str | Path) -> None:
        self._inner = inner
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.name = getattr(inner, "name", "provider")

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    async def complete(self, request: LLMRequest) -> ModelResponse:
        path = self._path(_key(request))
        if path.exists():
            data = json.loads(path.read_text())
            resp = ModelResponse.model_validate(data)
            resp.cached = True
            return resp

        resp = await self._inner.complete(request)
        # Never cache transient provider errors -- we want them retried next run.
        if resp.error is None:
            path.write_text(resp.model_dump_json())
        return resp
