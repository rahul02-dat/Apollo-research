"""LangGraph Checkpointer Factory."""

import logging
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def get_checkpointer(database_url: str | None = None) -> BaseCheckpointSaver:
    """Returns a LangGraph checkpointer suitable for the configured environment."""
    if database_url and database_url.startswith("postgresql"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore
            logger.info("Initializing PostgreSQL checkpointer from %s", database_url)
            return PostgresSaver.from_conn_string(database_url)
        except Exception as e:
            logger.warning("Failed to initialize PostgresSaver (%s). Falling back to MemorySaver.", e)

    logger.info("Using in-memory LangGraph checkpointer (MemorySaver).")
    return MemorySaver()
