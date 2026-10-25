import pytest
import re
import responses

from google_kit import Photos, GoogleError, GooglePhotosResult


UPLOAD_RE = re.compile(r"https://photoslibrary\.googleapis\.com/v1/uploads.*")
BATCH_RE = re.compile(r"https://photoslibrary\.googleapis\.com/v1/mediaItems:batchCreate.*")
ALBUMS_RE = re.compile(r"https://photoslibrary\.googleapis\.com/v1/albums.*")


def test_upload_media_item_happy(mock, auth):
    mock.add(responses.POST, UPLOAD_RE, body="upload-token", status=200)
    mock.add(
        responses.POST,
        BATCH_RE,
        json={
            "newMediaItemResults": [{
                "status": {"message": "Success"},
                "mediaItem": {"id": "mid1", "productUrl": "https://photos.google.com/xyz"},
            }]
        },
    )
    result = Photos(auth).upload_media_item(b"imgdata", "photo.jpg", "caption")

    assert isinstance(result, GooglePhotosResult)
    assert result.upload_token == "upload-token"
    assert result.media_item_id == "mid1"
    assert result.product_url == "https://photos.google.com/xyz"


def test_create_media_item_semantic_error_raises_google_error(mock, auth):
    mock.add(
        responses.POST,
        BATCH_RE,
        json={
            "newMediaItemResults": [{
                "status": {"message": "INVALID_ARGUMENT"},
            }]
        },
    )
    with pytest.raises(GoogleError) as error:
        Photos(auth).create_media_item("token", "photo.jpg", "cap")

    assert error.value.status == 200
    assert "INVALID_ARGUMENT" in str(error.value.body)


def test_create_album_happy(mock, auth):
    mock.add(
        responses.POST,
        ALBUMS_RE,
        json={"id": "album1", "title": "Trip"},
    )
    album = Photos(auth).create_album("Trip")

    assert album["id"] == "album1"


def test_add_media_items_happy(mock, auth):
    mock.add(
        responses.POST,
        re.compile(r"https://photoslibrary\.googleapis\.com/v1/albums/album1:batchAddMediaItems.*"),
        json={},
    )
    result = Photos(auth).add_media_items("album1", ["m1", "m2"])

    assert result == {}
