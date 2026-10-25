"""Minimal Google Drive REST helper: folders by path, files by name, upload/download."""
from __future__ import annotations

import json

from .auth import GoogleAuth
from .errors import raise_for_status

API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
SHEET = "application/vnd.google-apps.spreadsheet"
_BOUNDARY = "google-kit-boundary"


def _q(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class Drive:
    """Thin wrapper over the Drive v3 endpoints the services use."""

    def __init__(self, auth: GoogleAuth):
        self.s = auth.session()

    def list(self, parent: str = "root", mime: str | None = None, name: str | None = None) -> list[dict]:
        q = [f"'{parent}' in parents", "trashed = false"]
        if mime:
            q.append(f"mimeType = '{mime}'")
        if name:
            q.append(f"name = '{_q(name)}'")
        response = self.s.get(
            f"{API}/files",
            params={
                "q": " and ".join(q),
                "fields": "files(id,name,mimeType)",
                "pageSize": 200,
                "orderBy": "name",
            },
        )
        raise_for_status(response, "drive files.list")
        return response.json()["files"]

    def _create(self, name: str, mime: str, parent: str) -> str:
        response = self.s.post(
            f"{API}/files",
            params={"fields": "id"},
            json={"name": name, "mimeType": mime, "parents": [parent]},
        )
        raise_for_status(response, "drive files.create")
        return response.json()["id"]

    def ensure(self, name: str, mime: str, parent: str) -> str:
        found = self.list(parent, mime, name)
        return found[0]["id"] if found else self._create(name, mime, parent)

    def ensure_path(self, path: str) -> str:
        """'a/b/c' under My Drive; returns the id of the last folder. Existing folders are reused."""
        parent = "root"
        for part in filter(None, path.split("/")):
            parent = self.ensure(part, FOLDER, parent)
        return parent

    def ensure_spreadsheet(self, path: str, name: str) -> str:
        return self.ensure(name, SHEET, self.ensure_path(path))

    def upsert_file(self, parent: str, name: str, body: bytes, mime: str) -> str:
        """Create or replace file *name* in folder *parent*; returns the file id."""
        found = self.list(parent, name=name)
        if found:
            file_id = found[0]["id"]
            response = self.s.patch(
                f"{UPLOAD_API}/files/{file_id}",
                params={"uploadType": "media"},
                data=body,
                headers={"Content-Type": mime},
            )
        else:
            meta = json.dumps({"name": name, "parents": [parent], "mimeType": mime})
            payload = (
                f"--{_BOUNDARY}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                f"--{_BOUNDARY}\r\nContent-Type: {mime}\r\n\r\n"
            ).encode() + body + f"\r\n--{_BOUNDARY}--".encode()
            response = self.s.post(
                f"{UPLOAD_API}/files",
                params={"uploadType": "multipart", "fields": "id"},
                data=payload,
                headers={"Content-Type": f"multipart/related; boundary={_BOUNDARY}"},
            )
        raise_for_status(response, "drive files.upsert")
        return response.json()["id"]

    def upsert_json(self, parent: str, name: str, data: object) -> str:
        return self.upsert_file(parent, name, json.dumps(data, ensure_ascii=False).encode(), "application/json")

    def download(self, file_id: str) -> bytes:
        """Return the file content (Drive ``alt=media``)."""
        response = self.s.get(f"{API}/files/{file_id}", params={"alt": "media"})
        raise_for_status(response, "drive files.get")
        return response.content
