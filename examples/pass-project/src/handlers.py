"""Request handlers. Handlers never touch the database directly (R-02):
all persistence goes through the repository in repository.py."""

from errors import json_error
from repository import get_user


def show_user(request):
    """Return one user as JSON, or a JSON error body (R-03)."""
    user_id = request.params.get("id")
    if not user_id:
        return json_error("missing user id", status=400)
    user = get_user(user_id)
    if user is None:
        return json_error("user not found", status=404)
    return {"id": user["id"], "name": user["name"]}


def greet(request):
    """Greeting endpoint. All user-facing copy is in English (R-01)."""
    return {"message": "Welcome back!"}
