"""HTMX fragment routes — partial HTML without base layout."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from latincy_lexicon_site.pipeline import (
    analyze_paradigm_sync,
    analyze_word_sync,
)
from latincy_lexicon_site.templating import templates

router = APIRouter(prefix="/fragments")


@router.get("/word/{form}", response_class=HTMLResponse)
async def fragment_word(form: str, request: Request, pos: str | None = None):
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    cache_input = f"{form}|{pos or ''}"
    result = analyzer.get_or_compute(
        "word", cache_input, lambda _: analyze_word_sync(nlp, form, pos)
    )
    return templates.TemplateResponse(
        request=request, name="_word_entries.html", context={"result": result}
    )


@router.get("/paradigm/{lemma}", response_class=HTMLResponse)
async def fragment_paradigm(lemma: str, request: Request, pos: str | None = None):
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    cache_input = f"{lemma}|{pos or ''}"
    result = analyzer.get_or_compute(
        "paradigm", cache_input, lambda _: analyze_paradigm_sync(nlp, lemma, pos)
    )
    return templates.TemplateResponse(
        request=request, name="_paradigm_table.html", context={"result": result}
    )
