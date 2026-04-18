"""Shared slowapi limiter — imported by both the app and route modules.

Kept in its own module to avoid a circular import between main.py (which
attaches the limiter to app.state) and routes/api.py (which decorates
individual routes).
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def api_quota() -> str:
    """Re-read the env var each request so tests can tighten the quota."""
    return os.environ.get("LATINCY_SITE_API_QUOTA", "60/minute")
