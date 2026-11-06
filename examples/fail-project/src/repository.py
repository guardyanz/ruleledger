"""Persistence layer. This is the only module allowed to talk to the
database. Handlers call these functions instead (R-02)."""

from db import query


def get_user(user_id):
    """Fetch one user row by id. Returns a dict or None."""
    rows = query("SELECT id, name FROM users WHERE id = ?", (user_id,))
    return rows[0] if rows else None
