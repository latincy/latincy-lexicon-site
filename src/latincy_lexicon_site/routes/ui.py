"""Server-rendered HTML routes."""

from __future__ import annotations

import string

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from latincy_lexicon_site.flags import flags_enabled
from latincy_lexicon_site.pipeline import (
    analyze_paradigm_sync,
    analyze_sentence_sync,
    analyze_word_sync,
)
from latincy_lexicon_site.schemas import (
    SENTENCE_WORD_CAP,
    SentenceQuery,
    truncate_sentence,
)
from latincy_lexicon_site.templating import templates


def _base_context() -> dict:
    return {"flags_enabled": flags_enabled()}


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context=_base_context()
    )


@router.get("/sentence", response_class=HTMLResponse)
async def sentence_page(text: str, request: Request):
    try:
        validated = SentenceQuery(text=text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Single-word shortcut: send the user to the dedicated word page so they
    # get a bookmarkable /word/{form} URL and the fuller single-word layout.
    tokens = validated.text.split()
    if len(tokens) == 1:
        form = tokens[0].strip(string.punctuation)
        if form:
            return RedirectResponse(url=f"/word/{form}", status_code=302)

    processed, truncated, original_words = truncate_sentence(validated.text)
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    result = analyzer.get_or_compute(
        "sentence", processed, lambda x: analyze_sentence_sync(nlp, x)
    )
    return templates.TemplateResponse(
        request=request,
        name="sentence.html",
        context={
            **_base_context(),
            "result": result,
            "truncated": truncated,
            "original_word_count": original_words,
            "word_cap": SENTENCE_WORD_CAP,
        },
    )


@router.get("/word/{form}", response_class=HTMLResponse)
async def word_page(form: str, request: Request):
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    result = analyzer.get_or_compute(
        "word", form, lambda x: analyze_word_sync(nlp, x)
    )
    return templates.TemplateResponse(
        request=request,
        name="word.html",
        context={**_base_context(), "result": result},
    )


@router.get("/paradigm/{lemma}", response_class=HTMLResponse)
async def paradigm_page(lemma: str, request: Request, pos: str | None = None):
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    cache_input = f"{lemma}|{pos or ''}"
    result = analyzer.get_or_compute(
        "paradigm", cache_input, lambda _: analyze_paradigm_sync(nlp, lemma, pos)
    )
    return templates.TemplateResponse(
        request=request,
        name="paradigm.html",
        context={**_base_context(), "result": result},
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /word/\n"
        "Allow: /paradigm/\n"
        "Disallow: /api/\n"
        "Disallow: /fragments/\n"
        "Sitemap: https://lexicon.exploratoryphilology.org/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
async def sitemap(request: Request) -> Response:
    # v1: small static sitemap. v2 (TODO): enumerate lemmas from analyzer.
    base = "https://lexicon.exploratoryphilology.org"
    urls = [f"{base}/", f"{base}/word/amo", f"{base}/paradigm/amo"]
    body = "<?xml version='1.0' encoding='UTF-8'?>"
    body += "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
    for url in urls:
        body += f"<url><loc>{url}</loc></url>"
    body += "</urlset>"
    return Response(content=body, media_type="application/xml")
