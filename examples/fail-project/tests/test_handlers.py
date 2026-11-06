"""Tests for the public handler functions (R-05)."""


def test_show_user_returns_json_error_for_unknown_id(client):
    response = client.get("/users/nope")
    assert response.status_code == 404
    assert response.json["error"] == "user not found"


def test_greet_returns_english_message(client):
    response = client.get("/greet")
    assert response.json["message"] == "Welcome back!"
