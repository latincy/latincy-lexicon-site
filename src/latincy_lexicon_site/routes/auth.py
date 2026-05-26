"""Login / logout routes."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from latincy_lexicon_site.auth import verify_credentials
from latincy_lexicon_site.templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/"):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"next": next})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    if verify_credentials(username, password):
        request.session["user"] = username
        safe_next = next if next.startswith("/") and not next.startswith("//") else "/"
        return RedirectResponse(url=safe_next, status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Invalid username or password.", "next": next},
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
