"""The raw-failure-to-friendly-copy mapper shown in the library UI."""

import pytest

from app.api.error_messages import friendly_error


def test_none_and_empty_pass_through():
    assert friendly_error(None) is None
    assert friendly_error("") == ""


@pytest.mark.parametrize(
    "raw",
    [
        "Error code: 429 - insufficient_quota",
        "Rate limit reached for requests",
        "You exceeded your current quota, please check your billing",
    ],
)
def test_quota_and_rate_limits(raw):
    msg = friendly_error(raw)
    assert "quota" in msg.lower()
    assert "429" not in msg


@pytest.mark.parametrize(
    "raw",
    [
        "Error code: 401 - Incorrect API key provided: sk-123",
        "Illegal header value b'Bearer '",
        "AuthenticationError: Unauthorized",
    ],
)
def test_auth_and_key_problems(raw):
    msg = friendly_error(raw)
    assert "key" in msg.lower()
    assert "sk-123" not in msg


def test_timeout_is_transient():
    assert "try again" in friendly_error("Read timed out after 60s").lower()


def test_unknown_falls_back_without_leaking():
    raw = "Traceback: KeyError in assemble() at module.py:42"
    msg = friendly_error(raw)
    assert "went wrong" in msg.lower()
    assert "Traceback" not in msg
    assert "module.py" not in msg
