import pytest
import responses

from google_kit import Drive, GoogleError


API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"


def test_list_files(mock, auth):
    mock.add(
        responses.GET,
        f"{API}/files",
        json={"files": [{"id": "f1", "name": "a.txt", "mimeType": "text/plain"}]},
    )
    files = Drive(auth).list("folder-id", mime="text/plain", name="a.txt")

    assert files == [{"id": "f1", "name": "a.txt", "mimeType": "text/plain"}]
    # query params are URL-encoded
    assert "folder-id" in mock.calls[-1].request.url
    assert "text%2Fplain" in mock.calls[-1].request.url


def test_download(mock, auth):
    mock.add(responses.GET, f"{API}/files/f1", body=b"hello")
    data = Drive(auth).download("f1")

    assert data == b"hello"
    assert "alt=media" in mock.calls[-1].request.url


def test_upsert_file_create_multipart(mock, auth):
    # First GET to check if file exists
    mock.add(responses.GET, f"{API}/files", json={"files": []})
    # Then multipart POST to create
    mock.add(responses.POST, f"{UPLOAD_API}/files", json={"id": "new-id"})
    file_id = Drive(auth).upsert_file("parent", "new.txt", b"content", "text/plain")

    assert file_id == "new-id"
    assert mock.calls[-1].request.headers["Content-Type"].startswith("multipart/related")


def test_upsert_file_update_media(mock, auth):
    mock.add(responses.GET, f"{API}/files", json={"files": [{"id": "existing", "name": "a.txt"}]})
    mock.add(responses.PATCH, f"{UPLOAD_API}/files/existing", json={"id": "existing"})
    file_id = Drive(auth).upsert_file("parent", "a.txt", b"new content", "text/plain")

    assert file_id == "existing"


def test_download_error_raises_google_error(mock, auth):
    mock.add(responses.GET, f"{API}/files/missing", status=404, json={"error": {"message": "not found"}})

    with pytest.raises(GoogleError) as error:
        Drive(auth).download("missing")

    assert error.value.status == 404
    assert "not found" in error.value.body
