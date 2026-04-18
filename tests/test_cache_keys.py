from latincy_lexicon_site.cache import make_cache_key


def test_key_is_deterministic():
    k1 = make_cache_key("sentence", "arma virumque cano", version="v1")
    k2 = make_cache_key("sentence", "arma virumque cano", version="v1")
    assert k1 == k2


def test_key_differs_by_endpoint():
    k_sent = make_cache_key("sentence", "amo", version="v1")
    k_word = make_cache_key("word", "amo", version="v1")
    assert k_sent != k_word


def test_key_differs_by_version():
    k1 = make_cache_key("word", "amo", version="v1")
    k2 = make_cache_key("word", "amo", version="v2")
    assert k1 != k2


def test_key_normalizes_input():
    k1 = make_cache_key("word", "AMO", version="v1")
    k2 = make_cache_key("word", "amo", version="v1")
    assert k1 == k2
