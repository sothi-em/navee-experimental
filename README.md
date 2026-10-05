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

> Status: **experimental.** A streaming agent loop with tool execution, a
> skills store, per-user facts, optional vector recall, and transcript
> compaction are in place. It is a sandbox for iterating on long-form chat
> strategies, not a production system.

## Architecture (tiered state)

The chat transcript is treated as ephemeral working memory; durable state is
pushed into typed, owner-scoped, human-visible stores.

| Tier | Store | Lifetime |
|---|---|---|
| Working context | in-window chat history | trimmed / compacted each turn |
| Durable personal knowledge | learned facts (SQLite) | persistent, recalled by retrieval |
| Procedural knowledge | skills (TinyDB) | persistent, agent-saved |
| Semantic recall | flat-file ChromaDB index | persistent, optional |
| Full transcript | SQLite | persistent, human-visible |

## Repository layout

```
backend/    FastAPI + uv (Python 3.13)
  server.py         FastAPI app factory + entrypoint
  app/
    core/             config, SQLite store, TinyDB, session store, models
    agent/            llm, tokenizer, agent loop, memory/recall, tools
    api/routes/       health, users, chat, memory, skills, user_data
  tests/              API + store tests
frontend/   React + Vite + TypeScript + Tailwind CSS
  src/
    api/client.ts     typed backend client
    App.tsx           dashboard shell
    components/       ChatPanel, ThreadRail, MemoryPanel, SettingsModal, TopBar
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
uv run uvicorn server:app --reload --port 8000
```

> The venv lives at `backend/.venv` (uv projects live in `backend/`, not the
> repo root). In PyCharm, set the project interpreter to
> `backend/.venv`, not a root-level venv.

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
| `LLM_BASE_URL` | `http://127.0.0.1:8001/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | `not-set` | API key (often a dummy for local) |
| `LLM_MODEL` | `local-model` | model name to request |
| `TOKENIZER_NAME` | `gpt2` | HF tokenizer id or local path |
| `DATABASE_PATH` | `data/navee.db` | SQLite file (users, transcript, compactions, user facts) |
| `TINYDB_PATH` | `data/navee.json` | sessions + skills store |
| `CHROMA_PATH` | `data/chroma` | flat-file vector index |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | allowed origins |
| `CONVERSE_TOKEN_BUDGET` | `64000` | total per-turn context envelope (tokens) |
| `COMPACTION_BUDGET` | `16384` | cap for the compaction summary |
| `SKILL_BUDGET` | `8192` | cap for skill references |
| `USER_FACTS_BUDGET` | `1024` | cap for the user-facts summary |

## Testing

```bash
cd backend
uv run pytest
```

## Python libraries

- `sqlite3` (stdlib) — users, transcript, compaction history, user facts
- `tinydb` — sessions + skills
- `chromadb` — flat-file (persistent) semantic recall index
- `transformers` — tokenizer for token counting and chunking
- `openai` — client for the locally hosted LLM

## License

MIT — see [LICENSE](LICENSE).
