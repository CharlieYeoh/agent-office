"""
memory/db.py – SQLite-backed long-term memory for agents.

Each row stores a single memory entry with:
  - agent_name  : which agent owns this memory
  - role        : 'user' | 'assistant' | 'system'
  - content     : the text content of the memory
  - created_at  : ISO-8601 timestamp
"""

import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "agent_memory.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the memories table if it doesn't exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name  TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
            """
        )
        conn.commit()


def save_memory(agent_name: str, role: str, content: str):
    """Persist a single message to the database."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO memories (agent_name, role, content, created_at) VALUES (?, ?, ?, ?)",
            (agent_name, role, content, now),
        )
        conn.commit()


def load_memories(agent_name: str, limit: int = 50) -> list[dict]:
    """
    Retrieve the most recent *limit* memories for an agent.
    Returns a list of dicts with keys: id, agent_name, role, content, created_at.
    """
    init_db()
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, agent_name, role, content, created_at
            FROM memories
            WHERE agent_name = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (agent_name, limit),
        ).fetchall()
    # Return in chronological order
    return [dict(row) for row in reversed(rows)]


def clear_memories(agent_name: str):
    """Delete all memories for a given agent."""
    init_db()
    with _get_connection() as conn:
        conn.execute("DELETE FROM memories WHERE agent_name = ?", (agent_name,))
        conn.commit()
