"""Retry rules shared by the platform connectors."""

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
MAX_DELAY_SECONDS = 30.0


def retry_delay(retry_after: str | None, attempt: int) -> float:
    """Seconds to wait before the next attempt: Retry-After when given, else 1, 2, 4 ..."""
    if retry_after:
        try:
            return max(0.0, min(float(retry_after), MAX_DELAY_SECONDS))
        except ValueError:
            pass
    return min(float(2 ** attempt), MAX_DELAY_SECONDS)
