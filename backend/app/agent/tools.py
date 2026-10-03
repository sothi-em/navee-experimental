"""Agent tool registry.

All tools live in this module. Each tool is a `Tool` with a name, a
description (for the model), a JSON-schema `parameters` object, and a
callable. Real tools (memory, skills, RAG, transcript search) are added to
TOOLS here.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments object
    fn: Callable[..., Any]


def _echo(text: str) -> str:
    return text


def _get_current_time() -> str:
    return datetime.now(UTC).isoformat()


TOOLS: list[Tool] = [
    Tool(
        name="echo",
        description="Echo the input text back. Stub for real agent tools.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to echo"}},
            "required": ["text"],
        },
        fn=_echo,
    ),
    Tool(
        name="get_current_time",
        description="Get the current UTC time as an ISO 8601 string.",
        parameters={"type": "object", "properties": {}},
        fn=_get_current_time,
    ),
]


def get_tool(name: str) -> Tool | None:
    return next((t for t in TOOLS if t.name == name), None)


def all_tools() -> list[Tool]:
    return list(TOOLS)


def tool_specs() -> list[dict]:
    """OpenAI function-calling definitions for the whole registry."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in TOOLS
    ]
