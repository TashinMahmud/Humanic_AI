"""
Humanic AI – Chat History Manager (SQLite)
Persists conversation messages so history survives reconnects.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_db_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """Lazy-init a SQLite connection with WAL mode for concurrency."""
    global _db_conn
    if _db_conn is None:
        db_dir = Path(settings.CHAT_DB_DIR)
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "chat_history.db"
        _db_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
        _db_conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(_db_conn)
        logger.info("Chat history DB ready: %s", db_path)
    return _db_conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            timestamp   TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_session
        ON messages (session_id, timestamp)
    """)
    conn.commit()


# ── Public API ──

def add_message(session_id: str, role: str, content: str) -> str:
    """Save a message to the history. Returns the message id."""
    conn = _get_conn()
    msg_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return msg_id


def get_history(session_id: str, limit: int = 20) -> list[dict]:
    """Return the last `limit` messages for a session, oldest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    # Reverse so oldest is first (chronological order)
    return [dict(r) for r in reversed(rows)]


def create_session() -> str:
    """Generate a new session ID."""
    return str(uuid.uuid4())
