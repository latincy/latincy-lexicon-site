"""Session-based auth: middleware + credential verification against htpasswd file."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from passlib.apache import HtpasswdFile

_PUBLIC_PATHS = frozenset({"/login", "/healthz"})
_PUBLIC_PREFIXES = ("/static/",)


def auth_required() -> bool:
    """Login gate is on by default; set LATINCY_SITE_REQUIRE_AUTH=0 to open the site."""
    return os.environ.get("LATINCY_SITE_REQUIRE_AUTH", "1").lower() not in {"0", "false", "no", "off"}


def _htpasswd() -> HtpasswdFile:
    path = Path(os.environ.get("LATINCY_SITE_HTPASSWD", "/var/lib/latincy-lexicon-site/htpasswd"))
    return HtpasswdFile(path)


def verify_credentials(username: str, password: str) -> bool:
    try:
        ht = _htpasswd()
        ht.load_if_changed()
        return bool(ht.check_password(username, password))
    except Exception:
        return False


async def auth_middleware(request: Request, call_next):
    if not auth_required():
        return await call_next(request)
    path = request.url.path
    if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)
    if not request.session.get("user"):
        next_param = path if path != "/" else ""
        redirect = f"/login?next={next_param}" if next_param else "/login"
        return RedirectResponse(url=redirect, status_code=302)
    return await call_next(request)
