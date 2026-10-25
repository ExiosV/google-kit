"""The single exception type raised by google_kit."""
from __future__ import annotations

from typing import Any

import requests


class GoogleError(RuntimeError):
    """A Google API call failed.

    Subclasses ``RuntimeError`` so existing ``except RuntimeError`` handlers keep working.
    ``status`` is the HTTP status code (``None`` for semantic failures such as an empty
    Photos batchCreate result); ``body`` is the response text or the offending payload.
    """

    def __init__(self, message: str, *, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def raise_for_status(response: requests.Response, context: str = "") -> None:
    """Raise :class:`GoogleError` for a non-2xx response, carrying status and body."""
    if response.ok:
        return
    body = (response.text or "")[:1000]
    prefix = f"{context}: " if context else ""
    message = f"{prefix}HTTP {response.status_code}"
    if body:
        message = f"{message} {body}"
    raise GoogleError(message, status=response.status_code, body=body)
