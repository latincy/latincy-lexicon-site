import asyncio

import pytest
from spacy.language import Language

from latincy_lexicon_site.pipeline import analyze_sentence_async, load_pipeline


@pytest.fixture(scope="module")
def nlp() -> Language:
    return load_pipeline("la_core_web_sm")


@pytest.mark.asyncio
async def test_async_wrapper_returns_same_shape(nlp: Language):
    result = await analyze_sentence_async(nlp, "amo te.")
    assert "tokens" in result
    assert isinstance(result["tokens"], list)


@pytest.mark.asyncio
async def test_concurrent_calls_complete(nlp: Language):
    tasks = [
        analyze_sentence_async(nlp, f"sentence {i} est bonum.")
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 3
    for r in results:
        assert "tokens" in r
