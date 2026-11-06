"""Error responses. Every API error returns a JSON body with an
``error`` field (R-03). No secrets are logged or returned (R-04)."""


def json_error(message, status):
    """Build a JSON error body. ``message`` must be a plain string."""
    return {"status": status, "error": message}
