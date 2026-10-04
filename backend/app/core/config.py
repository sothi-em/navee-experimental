"""Application settings.

All values can be overridden via environment variables (case-insensitive,
matching the field name) or a backend/.env file. No auth by design: this is an
experimental sandbox.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_SYSTEM_PROMPT = (
    "You are Navee, a helpful assistant.\n\n"
    "Grounding rules:\n"
    "- For questions that need factual information, answer strictly from "
    "facts you are certain of and from tool results given in this "
    "conversation. Do not pad answers with guesses, assumptions, or "
    "invented details.\n"
    "- If you do not have a reliable answer and no tool result covers it, "
    "say plainly that you don't know (or that you couldn't find it). Do "
    "not fabricate.\n"
    "- For casual conversation, opinion, brainstorming, or creative "
    "requests, reasoning and inference are fine.\n"
    "- Keep answers concise and directly responsive to what was asked."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # CORS — the Vite dev server origin.
    cors_origins: list[str] = ["http://localhost:5173"]

    # Storage locations (created on demand).
    database_path: str = "data/navee.db"
    tinydb_path: str = "data/navee.json"
    chroma_path: str = "data/chroma"

    # Locally hosted, OpenAI-compatible LLM endpoint (e.g. llama.cpp, vLLM,
    # Ollama's /v1). 127.0.0.1: 0.0.0.0 is a bind address and is not a valid
    # connect target on Windows.
    llm_base_url: str = "http://127.0.0.1:8001/v1"
    llm_api_key: str = "not-set"
    llm_model: str = "local-model"

    # HuggingFace tokenizer id or a local path used for token counting and
    # chunking. Point this at a local model dir for offline use.
    tokenizer_name: str = "gpt2"

    # Context budgets (tokens). converse_token_budget is the total per-turn
    # context envelope: SYSTEM_PROMPT + TOOL + SKILL (name + short description)
    # + USER_FACTS (user facts summary) + latest compaction + current turn
    # (agent + user message). The system prompt, tools, and current turn are
    # rolling (variable); skill_budget, user_facts_budget, and
    # compaction_budget are fixed allocations reserved up front.
    converse_token_budget: int = 64000
    compaction_budget: int = 16384  # cap for the summary of compacted old messages
    skill_budget: int = 8192        # cap for skill references (name + short description)
    user_facts_budget: int = 1024   # cap for the user facts summary

    # Base system prompt prepended to every chat turn (env-overridable).
    base_system_prompt: str = BASE_SYSTEM_PROMPT


settings = Settings()
