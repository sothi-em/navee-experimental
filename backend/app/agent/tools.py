"""Agent tool registry.

A minimal, explicit registry. Real tools (memory management, skills, RAG,
transcript search, etc.) will be added here in a later pass. Each tool exposes
a name, a description (for the model), and a callable.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]


def _echo(text: str) -> str:
    return text


TOOLS: list[Tool] = [
    Tool(
        name="echo",
        description="Echo the input back. Placeholder for real agent tools.",
        fn=_echo,
    ),
]


def get_tool(name: str) -> Tool | None:
    return next((t for t in TOOLS if t.name == name), None)


def all_tools() -> list[Tool]:
    return list(TOOLS)
