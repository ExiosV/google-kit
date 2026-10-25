"""Google Photos Library REST: upload bytes, create media items, album operations.

The source service injected an EXIF date into the file before uploading; that is
application/media logic and stays in the caller. This module only talks HTTP.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from .auth import GoogleAuth
from .errors import GoogleError, raise_for_status

API = "https://photoslibrary.googleapis.com/v1"
UPLOAD_URL = f"{API}/uploads"
BATCH_CREATE_URL = f"{API}/mediaItems:batchCreate"
ALBUMS_URL = f"{API}/albums"
UPLOAD_TIMEOUT = 120.0


@dataclass(frozen=True)
class GooglePhotosResult:
    upload_token: str
    media_item_id: str | None
    product_url: str | None


class Photos:
    """Thin wrapper over the Photos Library endpoints the services use."""

    def __init__(self, auth: GoogleAuth):
        self.s = auth.session()

    def upload_bytes(self, data: bytes, file_name: str) -> str:
        """Upload raw bytes; returns the upload token used by :meth:`create_media_item`."""
        response = self.s.post(
            UPLOAD_URL,
            headers={
                "X-Goog-Upload-Protocol": "raw",
                "X-Goog-Upload-File-Name": file_name,
                "Content-Type": "application/octet-stream",
            },
            data=data,
            timeout=UPLOAD_TIMEOUT,
        )
        raise_for_status(response, "photos upload")
        return response.text

    def create_media_item(self, upload_token: str, file_name: str, description: str = "") -> dict[str, Any]:
        """Create one media item from an upload token; returns the ``mediaItem`` object."""
        body = {
            "newMediaItems": [{
                "description": description[:1000],
                "simpleMediaItem": {
                    "uploadToken": upload_token,
                    "fileName": file_name[:255],
                },
            }],
        }
        response = self.s.post(BATCH_CREATE_URL, json=body, timeout=UPLOAD_TIMEOUT)
        raise_for_status(response, "photos mediaItems.batchCreate")
        payload = response.json()
        results = payload.get("newMediaItemResults", [])
        if not results:
            raise GoogleError(
                "Google Photos did not return any media item results.",
                status=response.status_code,
                body=payload,
            )
        result = results[0]
        status = result.get("status")
        if status and not _is_success_status(status):
            raise GoogleError(
                f"Google Photos upload failed: {status}",
                status=response.status_code,
                body=result,
            )
        media_item = result.get("mediaItem")
        if not media_item:
            raise GoogleError(
                "Google Photos did not return media item details.",
                status=response.status_code,
                body=result,
            )
        return media_item

    def upload_media_item(
        self,
        data: bytes,
        file_name: str,
        description: str = "",
    ) -> GooglePhotosResult:
        """Upload bytes and create the media item in one call."""
        upload_token = self.upload_bytes(data, file_name)
        media_item = self.create_media_item(upload_token, file_name, description)
        return GooglePhotosResult(
            upload_token=upload_token,
            media_item_id=media_item.get("id"),
            product_url=media_item.get("productUrl"),
        )

    def create_album(self, title: str) -> dict[str, Any]:
        """Create an album and return the album object."""
        response = self.s.post(ALBUMS_URL, json={"album": {"title": title}})
        raise_for_status(response, "photos albums.create")
        return response.json()

    def add_media_items(self, album_id: str, media_item_ids: list[str]) -> dict[str, Any]:
        """Add existing media items to an album."""
        response = self.s.post(
            f"{ALBUMS_URL}/{quote(album_id, safe='')}:batchAddMediaItems",
            json={"mediaItemIds": list(media_item_ids)},
        )
        raise_for_status(response, "photos albums.batchAddMediaItems")
        return response.json() if response.content else {}


def _is_success_status(status: object) -> bool:
    if isinstance(status, dict):
        message = status.get("message")
        if isinstance(message, str) and message.lower() == "success":
            return True
    return False
