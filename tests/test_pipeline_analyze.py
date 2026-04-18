import pytest
from spacy.language import Language

from latincy_lexicon_site.pipeline import (
    analyze_paradigm_sync,
    analyze_sentence_sync,
    analyze_word_sync,
    load_pipeline,
)


@pytest.fixture(scope="module")
def nlp() -> Language:
    return load_pipeline("la_core_web_sm")


def test_analyze_sentence_returns_tokens(nlp: Language):
    result = analyze_sentence_sync(nlp, "Poeta bonus carmina scribit.")
    assert "tokens" in result
    assert len(result["tokens"]) >= 4
    first = result["tokens"][0]
    assert {"text", "lemma", "pos", "morph", "entries"} <= first.keys()


def test_analyze_word_returns_analyses(nlp: Language):
    result = analyze_word_sync(nlp, "amabam")
    assert "form" in result
    assert "analyses" in result
    assert isinstance(result["analyses"], list)


def test_analyze_paradigm_returns_forms(nlp: Language):
    result = analyze_paradigm_sync(nlp, "amo")
    assert result["lemma"] == "amo"
    assert isinstance(result["forms"], list)
    assert len(result["forms"]) > 0
    first = result["forms"][0]
    assert "form" in first
    assert "feats" in first
