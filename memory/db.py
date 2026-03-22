import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("MEMORY_DB_PATH", "memory/agent_memory.db"))


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name  TEXT NOT NULL,
                session_id  TEXT,
                task        TEXT NOT NULL,
                result      TEXT NOT NULL,
                summary     TEXT,
                tags        TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name  TEXT NOT NULL,
                fact        TEXT NOT NULL,
                importance  INTEGER DEFAULT 1,
                created_at  TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(task, result, summary, tags,
                           content=memories, content_rowid=id);

            CREATE TRIGGER IF NOT EXISTS memories_ai
                AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, task, result, summary, tags)
                    VALUES (new.id, new.task, new.result,
                            coalesce(new.summary,''), coalesce(new.tags,''));
                END;
        """)


def save_memory(agent_name: str, task: str, result: str,
                summary: str = "", tags: list = None,
                session_id: str = "") -> int:
    """
    Save a completed task and its result to persistent memory.
    Returns the row ID.
    """
    init_db()
    tags_str = ",".join(tags) if tags else ""
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO memories
               (agent_name, session_id, task, result, summary, tags, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_name, session_id, task, result[:4000],
             summary, tags_str, datetime.utcnow().isoformat())
        )
        return cur.lastrowid


def search_memories(agent_name: str, query: str, limit: int = 5) -> list[dict]:
    """Full-text search through an agent's past tasks and results."""
    init_db()
    # FTS5 chokes on special characters — sanitize by keeping only words
    import re
    clean_query = " ".join(re.findall(r'\w+', query))[:200]
    if not clean_query:
        return get_recent_memories(agent_name, limit)
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT m.id, m.task, m.result, m.summary, m.tags, m.created_at
                   FROM memories m
                   JOIN memories_fts fts ON fts.rowid = m.id
                   WHERE m.agent_name = ?
                     AND memories_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (agent_name, clean_query, limit)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        # Fall back to recent memories if search fails
        return get_recent_memories(agent_name, limit)


def get_recent_memories(agent_name: str, limit: int = 5) -> list[dict]:
    """Get the most recent memories for an agent."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, task, result, summary, tags, created_at
               FROM memories
               WHERE agent_name = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (agent_name, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def save_fact(agent_name: str, fact: str, importance: int = 1):
    """Save a persistent fact — things the agent should always remember."""
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO facts (agent_name, fact, importance, created_at) VALUES (?,?,?,?)",
            (agent_name, fact, importance, datetime.utcnow().isoformat())
        )


def get_facts(agent_name: str) -> list[str]:
    """Get all persistent facts for an agent."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT fact FROM facts WHERE agent_name = ? ORDER BY importance DESC",
            (agent_name,)
        ).fetchall()
        return [r["fact"] for r in rows]


def build_memory_context(agent_name: str, current_task: str) -> str:
    """
    Build a memory context string to inject into an agent's prompt.
    Searches for relevant past work and includes recent sessions.
    """
    init_db()
    relevant   = search_memories(agent_name, current_task, limit=3)
    recent     = get_recent_memories(agent_name, limit=2)
    facts      = get_facts(agent_name)
    seen_ids   = set()
    all_items  = []

    for m in relevant + recent:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            all_items.append(m)

    if not all_items and not facts:
        return ""

    parts = ["--- MEMORY CONTEXT (from previous sessions) ---"]

    if facts:
        parts.append("Persistent facts:")
        for f in facts:
            parts.append(f"  • {f}")

    if all_items:
        parts.append("Relevant past work:")
        for m in all_items[:4]:
            date = m["created_at"][:10]
            task_short = m["task"][:100]
            summary = m.get("summary") or m["result"][:150]
            parts.append(f"  [{date}] Task: {task_short}")
            parts.append(f"           Result: {summary}")

    parts.append("--- END MEMORY CONTEXT ---\n")
    return "\n".join(parts)