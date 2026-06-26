"""JSON API routes (versioned at /api/v1)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from latincy_lexicon_site.pipeline import analyze_word_sync
from latincy_lexicon_site.rate_limit import api_quota, limiter

router = APIRouter(prefix="/api/v1")


@router.get("/word/{form}")
@limiter.limit(api_quota)
async def api_word(form: str, request: Request, pos: str | None = None) -> dict:
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    cache_input = f"{form}|{pos or ''}"
    return analyzer.get_or_compute(
        "word", cache_input, lambda _: analyze_word_sync(nlp, form, pos)
    )
