"""Shared provider HTTP error handling.

Turns an error response from a provider into an exception that includes the
provider's own message body, so a failed episode's ``error`` reads e.g.
``OpenAI returned 429: ... insufficient_quota ...`` instead of a bare status.
"""

import httpx


class ProviderError(RuntimeError):
    """A provider API returned an error response."""


def raise_for_provider(resp: httpx.Response, provider: str) -> None:
    """Raise ProviderError with the response body on any error status."""
    if resp.is_success:
        return
    body = resp.text.strip()
    if len(body) > 500:
        body = body[:500] + "…"
    detail = f"{provider} returned {resp.status_code}"
    raise ProviderError(f"{detail}: {body}" if body else detail)
