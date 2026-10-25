# google-kit

Shared Google OAuth loader and thin REST wrappers for the ExiosV services.
It replaces the `google_auth`, `gdrive`, `gsheets`, `gcal`, `gmail` and `google_photos`
modules that every service used to copy. Depends only on `requests`.

```python
from google_kit import GoogleAuth, Drive, Sheets, Calendar, Gmail, Photos, GoogleError

auth = GoogleAuth.from_env()              # reads GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN
drive = Drive(auth).list("root", mime="application/vnd.google-apps.folder")
sheets = Sheets(auth).append_range(spreadsheet_id, "A1", [["new", "row"]])
calendar = Calendar(auth).upsert_event("primary", {"id": "...", "summary": "Run", ...})
gmail = Gmail(auth).list_ids("from:alarm@example.com")
photos = Photos(auth).upload_media_item(b"img", "run.jpg", "morning run")
```

`GoogleError` subclasses `RuntimeError` and carries `.status` (HTTP code) and `.body` (response text
or payload), so existing `except RuntimeError` code keeps working.

## Install (vendoring)

App images are built on devicex2 without a registry and without credentials, so a private git
dependency cannot be installed in the Dockerfile. Each project commits a copy instead:

```bash
cd google-kit && scripts/vendor.sh ../health-sync   # writes src/google_kit/ (+ VENDORED.txt)
```

The project's setuptools `packages.find` (`where = ["src"]`) then ships it; add `requests` to its
dependencies. To change the client edit **this** repo, bump `__version__`, rerun `vendor.sh` in
every project (PR per project).

## Migration map (old function → google_kit call)

| Source module / function | google_kit equivalent |
|--------------------------|------------------------|
| `health_sync.connectors.google_auth.credentials("drive")` | `GoogleAuth.from_env()` |
| `health_sync.connectors.google_auth.credentials("calendar")` | `GoogleAuth(client_id=..., client_secret=..., refresh_token=os.environ["GOOGLE_CALENDAR_REFRESH_TOKEN"])` |
| `health_sync.connectors.google_auth.has_oauth()` | `google_kit.has_oauth()` |
| `health_sync.connectors.gdrive.Drive.list / ensure / ensure_path / ensure_spreadsheet / upsert_file / upsert_json` | `Drive(auth).<same>` |
| `health_sync.connectors.gdrive.Drive` (no download) | `Drive(auth).download(file_id)` — **new, not in any source** |
| `health_sync.connectors.gsheets.SheetsSink._open` → gspread calls | `Sheets(auth).get_all_values / read_range / update_range / append_range` |
| `health_sync.connectors.gcal.list_calendars()` | `Calendar(auth).list_calendars()` |
| `health_sync.connectors.gcal.GoogleCalendarSink._upsert` | `Calendar(auth).upsert_event(calendar_id, event)` |
| `tg_garmin_livetrack.gmail.Gmail(client_id, client_secret, refresh_token)` | `Gmail(GoogleAuth(...))` → `list_ids / get / email` |
| `tg_kartinke2googleph.google_photos.load_credentials(...)` | `GoogleAuth.from_env()` — **no interactive/headless OAuth, no token JSON file** |
| `tg_kartinke2googleph.google_photos.upload_media_item` | `Photos(auth).upload_media_item(data, file_name, description)` |
| `tg_kartinke2googleph.google_photos._upload_bytes` | `Photos(auth).upload_bytes(data, file_name)` |
| `tg_kartinke2googleph.google_photos._create_media_item` | `Photos(auth).create_media_item(upload_token, file_name, description)` |
| (no source counterpart) | `Photos(auth).create_album(title)` / `add_media_items(album_id, media_item_ids)` — **new, not in any source** |

## What is *not* ported from the sources

- Interactive OAuth (`InstalledAppFlow` local server / headless console) and token JSON
  file handling (`GOOGLE_TOKEN_JSON`). Those belong in a one-off CLI, not in a library.
- Service-account credentials (`GOOGLE_SERVICE_ACCOUNT_JSON` / file). The only consumer
  (`gsheets`) uses them via `gspread.service_account_from_dict`; supporting them here would
  require JWT signing (extra dependency). **TODO** if another service needs it.
- EXIF date injection before Photos upload (`tg_kartinke2googleph.media.inject_exif_date`).
  That is application/media logic and stays in the caller.
- Calendar event construction, retry/throttle logic, and the whole `GoogleCalendarSink` class.
  Those are application-level sinks, not thin HTTP wrappers.
- `gspread`-specific row-insertion semantics (`worksheet.insert_rows(row=2)`), the `Table`
  dataclasses, and the health-specific column headers.
- Any health-specific scopes (`DRIVE`, `CALENDAR_EVENTS`, `CALENDAR_LIST`) — the library
  assumes the refresh token already carries the needed scopes.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```
