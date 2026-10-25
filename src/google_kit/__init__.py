"""Shared Google OAuth loader and thin REST wrappers for the ExiosV services (vendored, see README)."""
from .auth import GoogleAuth, has_oauth
from .calendar import Calendar
from .drive import Drive
from .errors import GoogleError
from .gmail import Gmail
from .photos import GooglePhotosResult, Photos
from .sheets import Sheets

__version__ = "0.1.1"
__all__ = [
    "Calendar",
    "Drive",
    "Gmail",
    "GoogleAuth",
    "GoogleError",
    "GooglePhotosResult",
    "Photos",
    "Sheets",
    "has_oauth",
    "__version__",
]
