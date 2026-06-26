"""Server-rendered HTML routes."""

from __future__ import annotations

import string

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from latincy_lexicon_site.flags import flags_enabled
from latincy_lexicon_site.pipeline import analyze_word_sync
from latincy_lexicon_site.templating import templates


def _base_context() -> dict:
    return {"flags_enabled": flags_enabled()}


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context=_base_context()
    )


@router.get("/word/{form}", response_class=HTMLResponse)
async def word_page(form: str, request: Request, pos: str | None = None):
    analyzer = request.app.state.analyzer
    nlp = request.app.state.nlp
    cache_input = f"{form}|{pos or ''}"
    result = analyzer.get_or_compute(
        "word", cache_input, lambda _: analyze_word_sync(nlp, form, pos)
    )
    return templates.TemplateResponse(
        request=request,
        name="word.html",
        context={**_base_context(), "result": result},
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /word/\n"
        "Disallow: /api/\n"
        "Disallow: /fragments/\n"
        "Sitemap: https://lexicon.exploratoryphilology.org/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
async def sitemap(request: Request) -> Response:
    base = "https://lexicon.exploratoryphilology.org"
    urls = [f"{base}/", f"{base}/word/amo", f"{base}/word/amor"]
    body = "<?xml version='1.0' encoding='UTF-8'?>"
    body += "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
    for url in urls:
        body += f"<url><loc>{url}</loc></url>"
    body += "</urlset>"
    return Response(content=body, media_type="application/xml")
