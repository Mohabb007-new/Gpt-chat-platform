import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "data/conversations.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_message(session_id: str, role: str, content: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )


def get_messages(session_id: str, limit: int = 10):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def list_sessions():
    with _connect() as conn:
        rows = conn.execute("""
            SELECT session_id,
                   COUNT(*) as msg_count,
                   MAX(created_at) as last_active,
                   (SELECT content FROM messages m2
                    WHERE m2.session_id = m.session_id AND m2.role = 'user'
                    ORDER BY created_at ASC LIMIT 1) as first_message
            FROM messages m
            GROUP BY session_id
            ORDER BY last_active DESC
        """).fetchall()
    return [
        {
            "session_id": r["session_id"],
            "message_count": r["msg_count"],
            "last_active": r["last_active"],
            "preview": (r["first_message"] or "")[:60],
        }
        for r in rows
    ]


def delete_session(session_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
