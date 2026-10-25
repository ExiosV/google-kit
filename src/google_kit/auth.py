"""Google OAuth: a refresh token traded for access tokens, cached until expiry.

Only the refresh-token flow is supported. It is the flow every source service used
(``GOOGLE_CLIENT_ID`` + ``GOOGLE_CLIENT_SECRET`` + ``GOOGLE_REFRESH_TOKEN``); interactive
consent and service accounts are left to a separate one-off tool.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from .errors import GoogleError

TOKEN_URI = "https://oauth2.googleapis.com/token"
DEFAULT_TIMEOUT = 30.0
# Refresh a little before the token really expires, so a request started at the edge
# does not arrive with a token that died in flight.
EXPIRY_MARGIN = 60.0


class GoogleAuth:
    """Refresh-token credentials shared by all wrapper classes."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        *,
        token_uri: str = TOKEN_URI,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        missing = [name for name, value in (
            ("client_id", client_id), ("client_secret", client_secret), ("refresh_token", refresh_token),
        ) if not value]
        if missing:
            raise ValueError(f"GoogleAuth is missing {', '.join(missing)}")
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.token_uri = token_uri
        self.timeout = timeout
        self._token: str | None = None
        self._expires_at = 0.0

    @classmethod
    def from_env(cls, prefix: str = "GOOGLE_") -> "GoogleAuth":
        """Read ``<prefix>CLIENT_ID``, ``<prefix>CLIENT_SECRET`` and ``<prefix>REFRESH_TOKEN``."""
        names = (f"{prefix}CLIENT_ID", f"{prefix}CLIENT_SECRET", f"{prefix}REFRESH_TOKEN")
        missing = [name for name in names if not os.getenv(name)]
        if missing:
            raise KeyError(f"missing Google OAuth environment variables: {', '.join(missing)}")
        return cls(*(os.environ[name] for name in names))

    def access_token(self, *, force: bool = False) -> str:
        """Return a valid access token, refreshing it only when needed (or when *force*)."""
        if not force and self._token and time.time() < self._expires_at:
            return self._token
        payload = self._refresh()
        self._token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 3600))
        # Never spend more than half a short-lived token on the safety margin.
        self._expires_at = time.time() + expires_in - min(EXPIRY_MARGIN, expires_in / 2)
        return self._token

    def _refresh(self) -> dict[str, Any]:
        response = requests.post(
            self.token_uri,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=self.timeout,
        )
        if not response.ok:
            raise GoogleError(
                f"google token refresh failed: HTTP {response.status_code}",
                status=response.status_code,
                body=(response.text or "")[:1000],
            )
        try:
            payload = response.json()
        except ValueError:
            raise GoogleError(
                "google token refresh returned invalid JSON",
                status=response.status_code,
                body=(response.text or "")[:1000],
            ) from None
        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise GoogleError(
                "google token refresh returned no access_token",
                status=response.status_code,
                body=payload,
            )
        return payload

    def session(self) -> requests.Session:
        """A ``requests.Session`` carrying the Bearer header; refreshes once on a 401."""
        return _AuthSession(self)


def has_oauth(prefix: str = "GOOGLE_") -> bool:
    """True when all three refresh-token variables are set (mirrors the old ``has_oauth()``)."""
    return all(os.getenv(f"{prefix}{suffix}") for suffix in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"))


class _AuthSession(requests.Session):
    def __init__(self, auth: GoogleAuth):
        super().__init__()
        self._auth = auth
        self.headers["Authorization"] = f"Bearer {auth.access_token()}"

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self._auth.timeout)
        response = super().request(method, url, **kwargs)
        if response.status_code == 401:
            response.close()
            self.headers["Authorization"] = f"Bearer {self._auth.access_token(force=True)}"
            response = super().request(method, url, **kwargs)
        return response
