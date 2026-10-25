import pytest
import re
import responses

from google_kit import Calendar, GoogleError


API = "https://www.googleapis.com/calendar/v3"
CALENDAR_RE = re.compile(rf"{API}/calendars/primary/events.*")
CAL_LIST_RE = re.compile(rf"{API}/users/me/calendarList.*")


def test_list_calendars(mock, auth):
    mock.add(
        responses.GET,
        CAL_LIST_RE,
        json={"items": [{"id": "primary", "summary": "Primary", "timeZone": "UTC", "primary": True}]},
    )
    cals = Calendar(auth).list_calendars()

    assert cals == [{"id": "primary", "summary": "Primary", "timeZone": "UTC", "primary": True}]


def test_list_events(mock, auth):
    mock.add(
        responses.GET,
        CALENDAR_RE,
        json={"items": [{"id": "evt1", "summary": "Test"}]},
    )
    events = Calendar(auth).list_events("primary", timeMin="2024-01-01T00:00:00Z", singleEvents="true")

    assert events == [{"id": "evt1", "summary": "Test"}]
    # URL has encoded colons
    assert "timeMin=2024-01-01T00%3A00%3A00Z" in mock.calls[-1].request.url


def test_insert_event(mock, auth):
    mock.add(responses.POST, CALENDAR_RE, json={"id": "evt1", "summary": "New"})
    event = Calendar(auth).insert_event("primary", {"summary": "New"})

    assert event == {"id": "evt1", "summary": "New"}


def test_upsert_event_409_patches(mock, auth):
    mock.add(responses.POST, CALENDAR_RE, status=409, json={"error": "conflict"})
    mock.add(responses.PATCH, re.compile(rf"{API}/calendars/primary/events/evt1"), json={"id": "evt1", "summary": "Updated", "status": "confirmed"})
    event = Calendar(auth).upsert_event("primary", {"id": "evt1", "summary": "New"})

    assert event["status"] == "confirmed"
    # PreparedRequest.body is bytes
    import json as _json
    body = _json.loads(mock.calls[-1].request.body)
    assert body == {"summary": "New", "status": "confirmed"}


def test_insert_event_error_raises_google_error(mock, auth):
    mock.add(responses.POST, CALENDAR_RE, status=400, json={"error": {"message": "bad request"}})

    with pytest.raises(GoogleError) as error:
        Calendar(auth).insert_event("primary", {"summary": "X"})

    assert error.value.status == 400
    assert "bad request" in error.value.body
