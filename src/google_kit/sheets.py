"""Minimal Google Sheets REST helper: read a range, update a range, append rows."""
from __future__ import annotations

from urllib.parse import quote

from .auth import GoogleAuth
from .errors import raise_for_status

API = "https://sheets.googleapis.com/v4/spreadsheets"


def _range(range_name: str) -> str:
    # A quoted worksheet title ('Sheet 1') and A1 notation both survive this encoding.
    return quote(range_name, safe="")


class Sheets:
    """Thin wrapper over the Sheets v4 values endpoints the services use."""

    def __init__(self, auth: GoogleAuth):
        self.s = auth.session()

    def get_all_values(self, spreadsheet_id: str, worksheet: str | None = None) -> list[list]:
        """All values of a worksheet (gspread ``worksheet.get_all_values()``)."""
        return self.read_range(spreadsheet_id, worksheet or "A:ZZ")

    def read_range(self, spreadsheet_id: str, range_name: str) -> list[list]:
        response = self.s.get(f"{API}/{spreadsheet_id}/values/{_range(range_name)}")
        raise_for_status(response, "sheets values.get")
        return response.json().get("values", [])

    def update_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list],
        *,
        value_input_option: str = "RAW",
    ) -> dict:
        """Replace the range with *values* (gspread ``worksheet.update(range_name=..., values=...)``)."""
        response = self.s.put(
            f"{API}/{spreadsheet_id}/values/{_range(range_name)}",
            params={"valueInputOption": value_input_option},
            json={"values": values},
        )
        raise_for_status(response, "sheets values.update")
        return response.json()

    def append_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list],
        *,
        value_input_option: str = "RAW",
        insert_data_option: str | None = None,
    ) -> dict:
        """Append rows after the last row of the range (Sheets ``values.append``)."""
        params = {"valueInputOption": value_input_option}
        if insert_data_option:
            params["insertDataOption"] = insert_data_option
        response = self.s.post(
            f"{API}/{spreadsheet_id}/values/{_range(range_name)}:append",
            params=params,
            json={"values": values},
        )
        raise_for_status(response, "sheets values.append")
        return response.json()
