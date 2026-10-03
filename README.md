# navee-experimental

Visualizing and testing various strategies of long-form user-agent
interactions.

This is an experimental sandbox: a **React dashboard** that talks to a
**FastAPI backend**, driving a long-running LLM agent chat. The agent has
tools, recall strategies, and learned facts/skills that live in **external,
persistent stores**, alongside a **full, durable copy of the transcript**
(the transcript is the record of what happened, not the model's live context).

There is no login or security — just simple users with normal attributes
(id, username, display name).

> Status: **scaffold.** The wiring, storage, and a minimal chat loop are in
> place. The agent loop, streaming, tool execution, context shaping, and
> recall strategies are the next phase. See
> [`docs/chat-memory-architecture.md`](docs/chat-memory-architecture.md) for
> the target design.

## Architecture (tiered state)

The chat transcript is treated as ephemeral working memory; durable state is
pushed into typed, owner-scoped, human-visible stores.

| Tier | Store | Lifetime |
|---|---|---|
| Working context | in-window chat history | trimmed / compacted each turn |
| Durable personal knowledge | learned facts (TinyDB) | persistent, recalled by retrieval |
| Procedural knowledge | skills (TinyDB) | persistent, agent-saved |
| Semantic recall | flat-file ChromaDB index | persistent, optional |
| Full transcript | SQLite | persistent, human-visible |

## Repository layout

```
backend/    FastAPI + uv (Python 3.13)
  app/
    main.py           app factory + entrypoint
    core/             config, SQLite store, pydantic models
    agent/            llm, tokenizer, memory/recall, tools
    api/routes/       health, users, chat
  tests/              API smoke tests
frontend/   React + Vite + TypeScript + Tailwind CSS
  src/
    api/client.ts     typed backend client
    App.tsx           dashboard (users + chat)
docs/       architecture & strategy notes
```

## Prerequisites

- **Python 3.13** (managed by `uv`; the backend pins `3.13.13`)
- **Node.js 18+**
- A **locally hosted, OpenAI-compatible LLM** (e.g. llama.cpp, vLLM, Ollama)

## Quick start

### 1. Backend

```bash
cd backend
uv sync --all-extras          # install deps into .venv
cp .env.example .env          # then set LLM_* and TOKENIZER_NAME
uv run uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Point `LLM_BASE_URL` / `LLM_MODEL` at your local model server.
- Point `TOKENIZER_NAME` at a local tokenizer/model dir for offline token
  counting and chunking.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Add a user, start a session, and chat. The dev
server proxies `/api/*` to the backend.

## Configuration

Backend settings come from environment variables or `backend/.env` (see
`backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8080/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | `not-set` | API key (often a dummy for local) |
| `LLM_MODEL` | `local-model` | model name to request |
| `TOKENIZER_NAME` | `gpt2` | HF tokenizer id or local path |
| `DATABASE_PATH` | `data/navee.db` | SQLite file |
| `TINYDB_PATH` | `data/navee.json` | facts + skills store |
| `CHROMA_PATH` | `data/chroma` | flat-file vector index |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | allowed origins |

## Testing

```bash
cd backend
uv run pytest
```

## Python libraries

- `sqlite3` (stdlib) — users, sessions, transcript
- `tinydb` — learned facts + skills
- `chromadb` — flat-file (persistent) semantic recall index
- `transformers` — tokenizer for token counting and chunking
- `openai` — client for the locally hosted LLM

## License

MIT — see [LICENSE](LICENSE).
