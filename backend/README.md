# Navee Backend

FastAPI backend for long-form LLM agent chat experiments. Python 3.13, managed
with `uv`.

## Stack

- **FastAPI + uvicorn** — HTTP API
- **SQLite** (`sqlite3`) — users, full transcript, compaction history
- **TinyDB** — sessions (transcript window), learned facts + skills (lightweight, human-editable)
- **ChromaDB** (flat-file / persistent) — semantic recall index (optional)
- **transformers** — tokenizer for token counting and chunking
- **openai** — client for a locally hosted, OpenAI-compatible LLM

## Setup

```bash
cd backend
uv sync --all-extras        # creates .venv and installs deps
cp .env.example .env        # then point LLM_* / TOKENIZER_NAME at your local model
```

## Run

```bash
uv run navee                     # http://127.0.0.1:8000
uv run navee --port 9000 --host 0.0.0.0
```

Interactive docs: http://127.0.0.1:8000/docs

## Test

```bash
uv run pytest
```

## Layout

```
server.py            # FastAPI app factory + entrypoint
app/
  config.py          # settings (env / .env)
  core/
    database.py      # SQLite schema + connection helper
    models.py        # pydantic request/response models
  agent/
    llm.py           # OpenAI-compatible client for the local LLM
    tokenizer.py     # token counting + chunking
    memory.py        # FactStore (TinyDB) + VectorRecall (ChromaDB)
    tools.py         # tool registry
  api/routes/
    health.py        # /api/health
    users.py         # /api/users
    chat.py          # /api/chat/sessions + transcript
tests/
  test_api.py        # API smoke tests
```

## Notes

- No auth by design — simple users only (id, username, display_name).
- The agent loop, streaming, tool execution, context shaping, and recall
  injection are intentionally deferred. See
  `../docs/chat-memory-architecture.md` for the target design.
