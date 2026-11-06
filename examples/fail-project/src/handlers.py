"""Request handlers."""

from db import query
from errors import json_error


def show_user(request):
    """Return one user as JSON, or a JSON error body (R-03)."""
    user_id = request.params.get("id")
    if not user_id:
        return json_error("missing user id", status=400)
    rows = query("SELECT id, name FROM users WHERE id = ?", (user_id,))
    if not rows:
        return json_error("user not found", status=404)
    user = rows[0]
    return {"id": user["id"], "name": user["name"]}


def greet(request):
    """Greeting endpoint. All user-facing copy is in English (R-01)."""
    return {"message": "Welcome back!"}
