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

from app.agent.memory import SkillStore


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


def _get_skill(name: str) -> str:
    skill = SkillStore().get_skill_by_name(name)
    if skill is None:
        return f"error: skill '{name}' not found"
    return skill.get("content", "")


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
    Tool(
        name="get_skill",
        description="Fetch the full content of a skill by name.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The exact name of the skill to fetch"},
            },
            "required": ["name"],
        },
        fn=_get_skill,
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
