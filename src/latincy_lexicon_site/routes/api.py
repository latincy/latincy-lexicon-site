"""JSON API routes (versioned at /api/v1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from latincy_lexicon_site.pipeline import (
    analyze_paradigm_sync,
    analyze_sentence_sync,
    analyze_word_sync,
)
from latincy_lexicon_site.rate_limit import api_quota, limiter
from latincy_lexicon_site.schemas import (
    SENTENCE_WORD_CAP,
    SentenceQuery,
    truncate_sentence,
)

router = APIRouter(prefix="/api/v1")


@router.get("/word/{form}")
@limiter.limit(api_quota)
async def api_word(form: str, request: Request) -> dict:
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    return analyzer.get_or_compute(
        "word", form, lambda x: analyze_word_sync(nlp, x)
    )


@router.get("/sentence")
@limiter.limit(api_quota)
async def api_sentence(text: str, request: Request) -> dict:
    try:
        validated = SentenceQuery(text=text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    processed, truncated, original_words = truncate_sentence(validated.text)
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    result = analyzer.get_or_compute(
        "sentence", processed, lambda x: analyze_sentence_sync(nlp, x)
    )
    if truncated:
        result = {
            **result,
            "truncated": True,
            "original_word_count": original_words,
            "word_cap": SENTENCE_WORD_CAP,
        }
    return result


@router.get("/paradigm/{lemma}")
@limiter.limit(api_quota)
async def api_paradigm(
    lemma: str, request: Request, pos: str | None = None
) -> dict:
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    cache_input = f"{lemma}|{pos or ''}"
    return analyzer.get_or_compute(
        "paradigm", cache_input, lambda _: analyze_paradigm_sync(nlp, lemma, pos)
    )
