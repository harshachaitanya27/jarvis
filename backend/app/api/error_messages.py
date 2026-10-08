"""Translate raw failure reasons into calm, user-facing copy.

The raw provider/exception string is kept in the database and server logs for
debugging; what reaches the app is a plain-language summary with a suggested
next step — never stack traces, HTTP status codes, or header gibberish.
"""


def friendly_error(raw: str | None) -> str | None:
    """Map a stored failure reason to something safe to show a user.

    Returns ``None``/empty unchanged (no failure to describe). Unrecognised
    errors fall back to a generic message rather than leaking internals.
    """
    if not raw:
        return raw
    text = raw.lower()

    def has(*needles: str) -> bool:
        return any(n in text for n in needles)

    if has("quota", "insufficient_quota", "429", "rate limit", "too many requests", "billing"):
        return (
            "Your AI provider is out of quota or is rate-limiting requests. "
            "Check your plan or billing, then try again."
        )
    if has(
        "api key", "unauthorized", "401", "authentication", "incorrect api key",
        "invalid x-api-key", "bearer", "no openai key", "key configured", "permission",
    ):
        return "Your AI provider key looks invalid or missing. Re-add it, then try again."
    if has("timeout", "timed out", "connection", "network", "temporarily unavailable"):
        return "The AI provider didn't respond in time. Please try again in a moment."
    if has("500", "502", "503", "server error", "overloaded", "service unavailable"):
        return "Your AI provider had a temporary problem. Please try again shortly."
    return "Something went wrong while generating this episode. Please try again."
