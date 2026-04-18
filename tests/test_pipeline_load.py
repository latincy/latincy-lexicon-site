from latincy_lexicon_site.pipeline import load_pipeline


def test_pruned_pipes_disabled():
    nlp = load_pipeline("la_core_web_sm")
    names = nlp.pipe_names
    for disabled in ("parser", "ner", "senter", "normer"):
        assert disabled not in names, f"{disabled} should be disabled"


def test_required_pipes_present():
    nlp = load_pipeline("la_core_web_sm")
    names = nlp.pipe_names
    for required in (
        "tok2vec",
        "tagger",
        "morphologizer",
        "trainable_lemmatizer",
        "lookup_lemmatizer",
    ):
        assert required in names, f"{required} should be present"


def test_lexicon_components_added():
    nlp = load_pipeline("la_core_web_sm")
    names = nlp.pipe_names
    assert "whitakers_words" in names
    assert "paradigm_generator" in names
