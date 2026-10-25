import pytest
import re
import responses

from google_kit import Gmail, GoogleError


API = "https://gmail.googleapis.com/gmail/v1/users/me"
MESSAGES_RE = re.compile(rf"{API}/messages.*")
MESSAGE_RE = re.compile(rf"{API}/messages/.*")
PROFILE_RE = re.compile(rf"{API}/profile.*")


def test_list_ids(mock, auth):
    mock.add(
        responses.GET,
        MESSAGES_RE,
        json={"messages": [{"id": "m1"}, {"id": "m2"}]},
    )
    ids = Gmail(auth).list_ids("from:test", max_results=50)

    assert ids == ["m1", "m2"]


def test_get_message(mock, auth):
    mock.add(
        responses.GET,
        MESSAGE_RE,
        json={"id": "m1", "payload": {"headers": []}},
    )
    msg = Gmail(auth).get("m1")

    assert msg["id"] == "m1"


def test_email(mock, auth):
    mock.add(responses.GET, PROFILE_RE, json={"emailAddress": "user@example.com"})
    addr = Gmail(auth).email()

    assert addr == "user@example.com"


def test_get_message_error_raises_google_error(mock, auth):
    mock.add(responses.GET, MESSAGE_RE, status=404, json={"error": {"message": "not found"}})

    with pytest.raises(GoogleError) as error:
        Gmail(auth).get("missing")

    assert error.value.status == 404
    assert "not found" in error.value.body
