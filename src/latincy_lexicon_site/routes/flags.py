"""Flag submission endpoint — off by default via LATINCY_SITE_FLAGS_ENABLED."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from latincy_lexicon_site.flags import flags_enabled

router = APIRouter(prefix="/flags")


class FlagSubmission(BaseModel):
    target_type: str = Field(pattern="^(sentence|word|paradigm)$")
    subject: str = Field(min_length=1, max_length=500)
    issue: str = Field(min_length=1, max_length=60)
    target_ref: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=1000)


@router.post("/submit")
async def submit_flag(payload: FlagSubmission, request: Request) -> dict:
    if not flags_enabled():
        raise HTTPException(status_code=404)

    store = request.app.state.flags
    client = request.client.host if request.client else "unknown"
    client_hash = hashlib.sha1(client.encode()).hexdigest()[:12]
    flag_id = store.record(
        target_type=payload.target_type,
        subject=payload.subject,
        issue=payload.issue,
        target_ref=payload.target_ref,
        note=payload.note,
        client_ip_hash=client_hash,
    )
    return {"id": flag_id, "status": "recorded"}
