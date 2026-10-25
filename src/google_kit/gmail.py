"""Minimal Gmail REST helper: search message ids, fetch one message, account address."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .auth import GoogleAuth
from .errors import raise_for_status

API = "https://gmail.googleapis.com/gmail/v1/users/me"


class Gmail:
    """Thin wrapper over the Gmail v1 endpoints the services use."""

    def __init__(self, auth: GoogleAuth):
        self.s = auth.session()

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        response = self.s.get(f"{API}/{path}", params=params)
        raise_for_status(response, f"gmail {path}")
        return response.json()

    def list_ids(self, query: str, max_results: int = 50) -> list[str]:
        """Ids of messages matching a Gmail search query."""
        payload = self._get("messages", q=query, maxResults=max_results)
        return [message["id"] for message in payload.get("messages", [])]

    def get(self, msg_id: str) -> dict[str, Any]:
        """One full message payload."""
        return self._get(f"messages/{quote(msg_id, safe='')}", format="full")

    def email(self) -> str:
        """The authenticated account's e-mail address."""
        return self._get("profile")["emailAddress"]
