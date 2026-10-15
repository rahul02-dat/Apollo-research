"""LangGraph Checkpointer Factory with Durable Persistence and Fail-Closed Production Behavior."""

import logging
import sqlite3
from pathlib import Path
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from app.config import settings

logger = logging.getLogger(__name__)


def get_checkpointer(database_url: str | None = None) -> BaseCheckpointSaver:
    """Returns a LangGraph checkpointer suitable for the configured environment.

    In production:
    - PostgreSQL checkpoint failures are strictly fatal (no silent in-memory fallback).
    - Unconfigured or in-memory persistence is prohibited.

    In development:
    - Defaults to durable SQLite checkpoints or MemorySaver for local tests.
    """
    db_url = database_url or settings.DATABASE_URL

    # 1. PostgreSQL Checkpointer
    if db_url and db_url.startswith("postgresql"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore
            logger.info("Initializing PostgreSQL checkpointer from %s", db_url)
            return PostgresSaver.from_conn_string(db_url)
        except Exception as e:
            if settings.is_production:
                logger.error("FATAL: PostgreSQL checkpointer initialization failed in production: %s", e)
                raise RuntimeError(
                    f"Fatal PostgreSQL checkpointer initialization failure in production: {e}. "
                    "Silent fallback to in-memory checkpointing is prohibited in production."
                ) from e
            logger.warning("Failed to initialize PostgresSaver (%s). Falling back to MemorySaver in development mode.", e)
            return MemorySaver()

    # 2. SQLite Durable Checkpointer
    if db_url and (db_url.startswith("sqlite") or db_url.endswith(".db")):
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            sqlite_path = db_url.replace("sqlite:///", "") if db_url.startswith("sqlite:///") else db_url

            if sqlite_path == ":memory:":
                if settings.is_production:
                    raise RuntimeError("In-memory SQLite persistence is prohibited in production.")
                conn = sqlite3.connect(":memory:", check_same_thread=False)
                saver = SqliteSaver(conn)
                saver.setup()
                return saver
            else:
                db_file = Path(sqlite_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(str(db_file), check_same_thread=False)
                saver = SqliteSaver(conn)
                saver.setup()
                logger.info("Initialized durable SQLite checkpointer at %s", sqlite_path)
                return saver
        except Exception as e:
            if settings.is_production:
                raise RuntimeError(f"Fatal SQLite checkpointer failure in production: {e}") from e
            logger.warning("Failed to initialize SqliteSaver (%s). Falling back to MemorySaver in development mode.", e)
            return MemorySaver()

    # 3. In-Memory Checkpointer Fallback
    if settings.is_production:
        raise RuntimeError(
            "Production environment violation: Durable checkpointer (PostgreSQL or SQLite) is required. "
            "In-memory checkpointing is prohibited in production."
        )

    logger.info("Using in-memory LangGraph checkpointer (MemorySaver) for development/testing.")
    return MemorySaver()

