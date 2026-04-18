import pytest
from pydantic import ValidationError

from latincy_lexicon_site.schemas import SentenceQuery, truncate_sentence


def test_accepts_short_sentence():
    q = SentenceQuery(text="arma virumque cano")
    assert q.text == "arma virumque cano"


def test_accepts_over_50_words():
    """Over-cap inputs are accepted by the schema; truncation happens downstream."""
    q = SentenceQuery(text=" ".join(["verbum"] * 51))
    assert q.text.count("verbum") == 51


def test_rejects_empty_text():
    with pytest.raises(ValidationError):
        SentenceQuery(text="")


def test_truncate_short_returns_original():
    text, trunc, orig = truncate_sentence("arma virumque cano")
    assert text == "arma virumque cano"
    assert trunc is False
    assert orig == 3


def test_truncate_exactly_50_not_truncated():
    text = " ".join(["verbum"] * 50)
    out, trunc, orig = truncate_sentence(text)
    assert out == text
    assert trunc is False
    assert orig == 50


def test_truncate_over_50_truncates():
    text = " ".join(["verbum"] * 75)
    out, trunc, orig = truncate_sentence(text)
    assert trunc is True
    assert orig == 75
    assert len(out.split()) == 50
