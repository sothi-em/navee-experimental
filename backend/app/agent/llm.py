"""Thin wrapper over an OpenAI-compatible client for a locally hosted LLM.

Degrades gracefully when the endpoint is unreachable so the dashboard and
persistence keep working during setup.
"""

from openai import OpenAI

from app.core.config import settings


class LLMClient:
    def __init__(self) -> None:
        self._client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
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
