import pytest
import re
import responses
import json as _json

from google_kit import Sheets, GoogleError


API = "https://sheets.googleapis.com/v4/spreadsheets"
RANGE_RE = re.compile(rf"{API}/sheet1/values/.*")


def test_get_all_values(mock, auth):
    mock.add(
        responses.GET,
        RANGE_RE,
        json={"values": [["a", "b"], ["1", "2"]]},
    )
    values = Sheets(auth).get_all_values("sheet1", "Sheet 1")

    assert values == [["a", "b"], ["1", "2"]]


def test_read_range(mock, auth):
    mock.add(
        responses.GET,
        RANGE_RE,
        json={"values": [["x"]]},
    )
    values = Sheets(auth).read_range("sheet1", "A1:B2")
    assert values == [["x"]]


def test_update_range(mock, auth):
    mock.add(responses.PUT, RANGE_RE, json={"updatedCells": 4})
    result = Sheets(auth).update_range("sheet1", "A1:B2", [["a", "b"], ["c", "d"]])

    assert result == {"updatedCells": 4}
    assert "valueInputOption=RAW" in mock.calls[-1].request.url
    body = _json.loads(mock.calls[-1].request.body)
    assert body == {"values": [["a", "b"], ["c", "d"]]}


def test_append_range(mock, auth):
    mock.add(responses.POST, RANGE_RE, json={"updates": {"updatedRows": 1}})
    result = Sheets(auth).append_range("sheet1", "A1", [["row"]])

    assert result == {"updates": {"updatedRows": 1}}
    assert "valueInputOption=RAW" in mock.calls[-1].request.url


def test_update_range_error_raises_google_error(mock, auth):
    mock.add(responses.PUT, RANGE_RE, status=403, json={"error": {"message": "quota"}})

    with pytest.raises(GoogleError) as error:
        Sheets(auth).update_range("sheet1", "A1", [["x"]])

    assert error.value.status == 403
    assert "quota" in error.value.body
