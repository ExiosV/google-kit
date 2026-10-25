import pytest
import responses

from google_kit import GoogleAuth, GoogleError, has_oauth
from google_kit.auth import TOKEN_URI


def test_access_token_is_cached_until_expiry(mock):
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t1", "expires_in": 3600})
    auth = GoogleAuth("cid", "secret", "refresh")

    assert auth.access_token() == "t1"
    assert auth.access_token() == "t1"
    assert len(mock.calls) == 1
    assert "grant_type=refresh_token" in mock.calls[0].request.body


def test_token_is_refreshed_after_expiry(mock, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("google_kit.auth.time.time", lambda: now[0])
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t1", "expires_in": 3600})
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t2", "expires_in": 3600})
    auth = GoogleAuth("cid", "secret", "refresh")

    assert auth.access_token() == "t1"
    now[0] += 3600
    assert auth.access_token() == "t2"
    assert len(mock.calls) == 2


def test_session_sends_bearer_and_retries_once_on_401(mock):
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t1", "expires_in": 3600})
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t2", "expires_in": 3600})
    url = "https://example.test/thing"
    mock.add(responses.GET, url, status=401, json={"error": "expired"})
    mock.add(responses.GET, url, status=200, json={"ok": True})

    response = GoogleAuth("cid", "secret", "refresh").session().get(url)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    # call 0: POST token (no auth)
    # call 1: GET with Bearer t1 -> 401
    # call 2: POST token (no auth)
    # call 3: GET with Bearer t2
    assert mock.calls[1].request.headers["Authorization"] == "Bearer t1"
    assert mock.calls[2].request.headers.get("Authorization") is None
    assert mock.calls[3].request.headers["Authorization"] == "Bearer t2"


def test_second_401_is_not_retried_forever(mock):
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t1", "expires_in": 3600})
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "t2", "expires_in": 3600})
    url = "https://example.test/thing"
    mock.add(responses.GET, url, status=401)
    mock.add(responses.GET, url, status=401)

    assert GoogleAuth("cid", "secret", "refresh").session().get(url).status_code == 401
    assert len(mock.calls) == 4  # token, 401, token, 401


def test_token_endpoint_error_raises_google_error(mock):
    mock.add(responses.POST, TOKEN_URI, status=400, body="invalid_grant")

    with pytest.raises(GoogleError) as error:
        GoogleAuth("cid", "secret", "refresh").access_token()

    assert error.value.status == 400
    assert "invalid_grant" in error.value.body
    assert isinstance(error.value, RuntimeError)


def test_from_env_and_has_oauth(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh")

    auth = GoogleAuth.from_env()
    assert (auth.client_id, auth.client_secret, auth.refresh_token) == ("cid", "secret", "refresh")
    assert has_oauth()

    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN")
    assert not has_oauth()
    with pytest.raises(KeyError):
        GoogleAuth.from_env()
