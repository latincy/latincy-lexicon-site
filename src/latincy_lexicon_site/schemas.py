"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

SENTENCE_WORD_CAP = 50


class SentenceQuery(BaseModel):
    text: str = Field(min_length=1, description="Latin sentence.")


def truncate_sentence(text: str, cap: int = SENTENCE_WORD_CAP) -> tuple[str, bool, int]:
    """Return (possibly-truncated text, was_truncated, original_word_count).

    Whitespace-split is used for the cap check — cheap and matches what the
    user sees in the input. Actual token count after spaCy tokenization may
    differ for enclitics but stays below the cap in all observed cases.
    """
    words = text.split()
    original = len(words)
    if original <= cap:
        return text, False, original
    return " ".join(words[:cap]), True, original


class TokenOut(BaseModel):
    text: str
    lemma: str
    pos: str
    morph: str
    entries: list[dict]


class SentenceResponse(BaseModel):
    text: str
    tokens: list[TokenOut]


class WordResponse(BaseModel):
    form: str
    normalized: str
    analyses: list[dict]


class ParadigmForm(BaseModel):
    form: str
    upos: str | None
    feats: dict


class ParadigmResponse(BaseModel):
    lemma: str
    pos: str | None
    forms: list[ParadigmForm]
