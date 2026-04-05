from app.db import add_message, get_messages, delete_session as _db_delete


def add_to_memory(session_id: str, role: str, content: str):
    add_message(session_id, role, content)


def get_memory(session_id: str):
    return get_messages(session_id, limit=10)


def clear_memory(session_id: str):
    _db_delete(session_id)
