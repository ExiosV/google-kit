import pytest
import responses

from google_kit import GoogleAuth
from google_kit.auth import TOKEN_URI


@pytest.fixture
def mock():
    """A live ``responses`` mock; nothing reaches the network."""
    with responses.RequestsMock() as mocked:
        yield mocked


@pytest.fixture
def auth(mock):
    """A GoogleAuth whose token request is already registered on *mock*."""
    mock.add(responses.POST, TOKEN_URI, json={"access_token": "tok", "expires_in": 3600})
    return GoogleAuth("client-id", "client-secret", "refresh-token")
