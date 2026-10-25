"""Minimal Google Calendar REST helper: list calendars, list/insert/patch events."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .auth import GoogleAuth
from .errors import raise_for_status

API = "https://www.googleapis.com/calendar/v3"


def _calendar(calendar_id: str) -> str:
    return quote(calendar_id, safe="")


class Calendar:
    """Thin wrapper over the Calendar v3 endpoints the services use."""

    def __init__(self, auth: GoogleAuth):
        self.s = auth.session()

    def list_calendars(self) -> list[dict[str, Any]]:
        """All calendars visible to the account (id, summary, timeZone, primary)."""
        response = self.s.get(
            f"{API}/users/me/calendarList",
            params={"maxResults": 250, "fields": "items(id,summary,timeZone,primary)"},
        )
        raise_for_status(response, "calendar calendarList.list")
        return response.json().get("items", [])

    def list_events(self, calendar_id: str = "primary", **params: Any) -> list[dict[str, Any]]:
        """Events of one calendar; pass ``timeMin``/``timeMax``/``singleEvents`` etc. through."""
        response = self.s.get(f"{API}/calendars/{_calendar(calendar_id)}/events", params=params)
        raise_for_status(response, "calendar events.list")
        return response.json().get("items", [])

    def insert_event(
        self,
        calendar_id: str,
        event: dict[str, Any],
        *,
        send_updates: str = "none",
    ) -> dict[str, Any]:
        response = self.s.post(
            f"{API}/calendars/{_calendar(calendar_id)}/events",
            json=event,
            params={"sendUpdates": send_updates},
        )
        raise_for_status(response, "calendar events.insert")
        return response.json()

    def patch_event(
        self,
        calendar_id: str,
        event_id: str,
        event: dict[str, Any],
        *,
        send_updates: str = "none",
    ) -> dict[str, Any]:
        response = self.s.patch(
            f"{API}/calendars/{_calendar(calendar_id)}/events/{quote(event_id, safe='')}",
            json=event,
            params={"sendUpdates": send_updates},
        )
        raise_for_status(response, "calendar events.patch")
        return response.json()

    def upsert_event(
        self,
        calendar_id: str,
        event: dict[str, Any],
        *,
        send_updates: str = "none",
    ) -> dict[str, Any]:
        """Insert an event; on 409 update the existing event with the same id in place.

        Mirrors ``GoogleCalendarSink._upsert``: a deleted event keeps a ``cancelled``
        tombstone under the same id, so the patch also asks for ``status: confirmed``.
        """
        url = f"{API}/calendars/{_calendar(calendar_id)}/events"
        params = {"sendUpdates": send_updates}
        response = self.s.post(url, json=event, params=params)
        if response.status_code == 409:
            body = {k: v for k, v in event.items() if k != "id"}
            body["status"] = "confirmed"
            response = self.s.patch(f"{url}/{quote(event['id'], safe='')}", json=body, params=params)
        raise_for_status(response, "calendar events.upsert")
        return response.json()
