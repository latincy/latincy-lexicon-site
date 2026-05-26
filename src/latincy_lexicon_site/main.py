"""FastAPI app entry point."""

from __future__ import annotations

import hashlib
import os
import time
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from latincy_lexicon_site import __version__
from latincy_lexicon_site.auth import auth_middleware
from latincy_lexicon_site.cache import CachedAnalyzer, SqliteCache
from latincy_lexicon_site.flags import FlagStore
from latincy_lexicon_site.logging_setup import configure as configure_logging
from latincy_lexicon_site.logging_setup import logger
from latincy_lexicon_site.pipeline import load_pipeline, warmup
from latincy_lexicon_site.rate_limit import limiter

configure_logging()


def _build_cache_version() -> str:
    return (
        f"site={__version__}"
        f"|lexicon={pkg_version('latincy-lexicon')}"
        f"|model={os.environ.get('LATINCY_SITE_MODEL', 'la_core_web_lg')}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_name = os.environ.get("LATINCY_SITE_MODEL", "la_core_web_lg")
    cache_path = Path(
        os.environ.get("LATINCY_SITE_CACHE_PATH", "var/cache.db")
    )

    nlp = load_pipeline(model_name)
    warmup(nlp)

    sqlite = SqliteCache(cache_path)
    analyzer = CachedAnalyzer(sqlite, version=_build_cache_version())

    flags_path = Path(
        os.environ.get("LATINCY_SITE_FLAGS_PATH", str(cache_path.parent / "flags.db"))
    )
    flags = FlagStore(flags_path)

    app.state.nlp = nlp
    app.state.analyzer = analyzer
    app.state.sqlite = sqlite
    app.state.flags = flags
    app.state.model_name = model_name
    yield

    sqlite.close()
    flags.close()


app = FastAPI(
    title="latincy-lexicon-site",
    version=__version__,
    description="Latin dictionary lookup + sentence analysis + inflectional paradigms.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


_CACHE_POLICY: tuple[tuple[str, str, str], ...] = (
    # (match_type, path, Cache-Control value)
    ("prefix", "/fragments/", "no-store"),
    ("prefix", "/healthz", "no-store"),
    ("prefix", "/docs", "no-store"),
    ("prefix", "/openapi.json", "no-store"),
    ("exact", "/api/v1/sentence", "public, max-age=3600"),
    ("prefix", "/api/v1/word/", "public, max-age=86400"),
    ("prefix", "/api/v1/paradigm/", "public, max-age=86400"),
    ("exact", "/sentence", "public, max-age=3600"),
    ("prefix", "/word/", "public, max-age=86400"),
    ("prefix", "/paradigm/", "public, max-age=86400"),
)


def _cache_control_for(path: str) -> str | None:
    for kind, pattern, value in _CACHE_POLICY:
        if kind == "exact" and path == pattern:
            return value
        if kind == "prefix" and path.startswith(pattern):
            return value
    return None


@app.middleware("http")
async def _auth_check(request: Request, call_next):
    return await auth_middleware(request, call_next)


@app.middleware("http")
async def log_and_cache_control(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    cc = _cache_control_for(request.url.path)
    if cc and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = cc

    client = request.client.host if request.client else "unknown"
    client_hash = hashlib.sha1(client.encode()).hexdigest()[:12]
    logger.info(
        "request",
        path=request.url.path,
        method=request.method,
        status=response.status_code,
        duration_ms=round(duration_ms, 1),
        client_ip_hash=client_hash,
    )
    return response

from latincy_lexicon_site.routes import api as api_routes  # noqa: E402
from latincy_lexicon_site.routes import auth as auth_routes  # noqa: E402
from latincy_lexicon_site.routes import flags as flag_routes  # noqa: E402
from latincy_lexicon_site.routes import fragments as fragment_routes  # noqa: E402
from latincy_lexicon_site.routes import ui as ui_routes  # noqa: E402

app.include_router(auth_routes.router)
app.include_router(ui_routes.router)
app.include_router(api_routes.router)
app.include_router(fragment_routes.router)
app.include_router(flag_routes.router)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("LATINCY_SITE_SESSION_SECRET", "dev-secret-change-in-prod"),
    session_cookie="latincy_session",
    max_age=60 * 60 * 24 * 7,  # 1 week
    https_only=True,
)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.get("/healthz")
async def healthz() -> dict:
    return {
        "status": "ok",
        "versions": {
            "latincy_lexicon_site": __version__,
            "latincy_lexicon": pkg_version("latincy-lexicon"),
            "spacy_model": app.state.model_name,
        },
        "cache_rows": app.state.sqlite.rows(),
    }
