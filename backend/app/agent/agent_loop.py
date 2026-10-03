"""Streaming agent loop: model call → tool execution → repeat.

Consumes the LLM's stream, executes any requested tools, appends results to
the in-memory conversation, and loops until the model replies with plain text
or MAX_ROUNDS is hit. Yields event dicts (see the SSE protocol in the route).
The intermediate tool trace is NOT persisted — only the route persists the
final reply (plus tool_events metadata).
"""

import inspect
import json

from app.agent.llm import llm
from app.agent.tools import get_tool, tool_specs

MAX_ROUNDS = 8


async def run_agent_stream(messages: list[dict]):
    """Run the tool loop. `messages` is OpenAI-format history including the
    new user turn. Yields:
      {"type": "delta", "content": str}
      {"type": "tool_start", "id": str, "name": str, "arguments": dict}
      {"type": "tool", "id": str, "name": str, "arguments": dict, "result": str}
      {"type": "error", "message": str}   (terminal)
    """
    specs = tool_specs() or None
    convo = list(messages)
    for _ in range(MAX_ROUNDS):
        content_parts: list[str] = []
        tool_calls: dict[int, dict] = {}
        try:
            async for chunk in llm.stream_chat(convo, tools=specs):
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "delta", "content": delta.content}
                for tc in delta.tool_calls or []:
                    slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["arguments"] += tc.function.arguments
        except Exception as exc:  # noqa: BLE001 — surface any LLM failure as an event
            yield {"type": "error", "message": f"LLM error: {exc.__class__.__name__}: {exc}"}
            return
        if not tool_calls:
            return
        convo.append(
            {
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls.values()
                ],
            }
        )
        for tc in tool_calls.values():
            yield {
                "type": "tool_start",
                "id": tc["id"],
                "name": tc["name"],
                "arguments": _safe_json(tc["arguments"]),
            }
            result = await _execute_tool(tc)
            yield {
                "type": "tool",
                "id": tc["id"],
                "name": tc["name"],
                "arguments": _safe_json(tc["arguments"]),
                "result": result,
            }
            convo.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    yield {"type": "error", "message": f"agent stopped after {MAX_ROUNDS} tool rounds"}


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {"_raw": raw}


async def _execute_tool(tc: dict) -> str:
    tool = get_tool(tc["name"])
    if tool is None:
        return f"error: unknown tool '{tc['name']}'"
    args = _safe_json(tc["arguments"])
    if "_raw" in args:
        return f"error: invalid JSON arguments: {tc['arguments']}"
    try:
        result = tool.fn(**args)
        if inspect.iscoroutine(result):
            result = await result
        return str(result)
    except Exception as exc:  # noqa: BLE001 — tool errors go back to the model
        return f"error: {exc.__class__.__name__}: {exc}"
