"""Thin wrapper over an OpenAI-compatible client for a locally hosted LLM.

The sync `complete()` degrades gracefully when the endpoint is unreachable so
the dashboard and persistence keep working during setup. `stream_chat()`
raises on connection/API errors — the agent loop surfaces those as events.
"""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionChunk

from app.core.config import settings


class LLMClient:
    def __init__(self) -> None:
        self._client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        self._aclient = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        self.model = settings.llm_model

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Single non-streaming completion. Returns a placeholder string on error."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._client.chat.completions.create(model=self.model, messages=messages)
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001 — skeleton degrades on any LLM error
            return f"[LLM unavailable: {exc.__class__.__name__}]"

    async def stream_chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Streaming chat completion. Yields raw OpenAI chunks (content and
        tool_call deltas). Raises on connection/API errors — callers handle."""
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            kwargs["tools"] = tools
        stream = await self._aclient.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk


llm = LLMClient()
