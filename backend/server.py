"""FastAPI application factory and entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, health, memory, skills, user_data, users
from app.core.config import settings
from app.core.database import init_db, migrate_messages_schema, migrate_users_schema
from app.core.session_store import migrate_legacy_sessions


@asynccontextmanager
async def lifespan(_: FastAPI):
    # uvicorn's default log config only attaches handlers to the
    # ``uvicorn.*`` loggers, leaving the root logger handler-less; without
    # this, our own loggers' INFO messages are dropped. basicConfig is a
    # no-op when a handler is already present (e.g. custom log_config).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    init_db()
    migrate_messages_schema()
    migrate_users_schema()
    migrate_legacy_sessions()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Navee", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(memory.router)
    app.include_router(user_data.router)
    app.include_router(skills.router)
    app.include_router(chat.router)
    return app


app = create_app()


def main() -> None:
    """CLI entrypoint: ``uv run navee [--host H] [--port P]``."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(prog="navee", description="Run the Navee API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    args = parser.parse_args()
    print(f"Navee API: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
