"""Bucketing logic for paradigm rendering — sanity-check the shape of
layout dicts the template renders against."""

from latincy_lexicon_site.paradigm_layout import layout_paradigm


def _form(form, **feats):
    return {"form": form, "upos": feats.pop("upos", "VERB"), "feats": feats}


def test_empty_input_returns_empty_kind():
    assert layout_paradigm([], None) == {
        "kind": "empty", "blocks": [], "alternates": [], "total": 0,
    }


def test_verb_buckets_by_mood_then_voice():
    forms = [
        _form("amo", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
        _form("amor", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Pass", Person="1", Number="Sing"),
        _form("amem", VerbForm="Fin", Mood="Sub", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
    ]
    out = layout_paradigm(forms, "VERB")
    assert out["kind"] == "verb"
    titles = [b["title"] for b in out["blocks"] if b["kind"] == "finite"]
    assert "Indicative" in titles
    assert "Subjunctive" in titles
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    assert "Act" in ind["voices"] and "Pass" in ind["voices"]


def test_verb_drops_all_empty_rows():
    """Latin synthetic perfect passive doesn't exist; if every cell of
    a tense row across all voices is empty, the row should not render."""
    forms = [
        _form("amo", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
        _form("amor", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Pass", Person="1", Number="Sing"),
        _form("amavi", VerbForm="Fin", Mood="Ind", Tense="Past",
              Voice="Act", Person="1", Number="Sing"),
    ]
    out = layout_paradigm(forms, "VERB")
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    tenses = [r["tense"] for r in ind["rows"]]
    # "Past" has Active only, never empty across voices, so it stays
    assert "Past" in tenses


def test_adj_splits_by_degree():
    forms = [
        {"form": "bonus", "upos": "ADJ",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Masc",
                   "Degree": "Pos"}},
        {"form": "melior", "upos": "ADJ",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Com",
                   "Degree": "Cmp"}},
        {"form": "optimus", "upos": "ADJ",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Masc",
                   "Degree": "Sup"}},
    ]
    out = layout_paradigm(forms, "ADJ")
    titles = [b["title"] for b in out["blocks"]]
    assert titles == ["Positive", "Comparative", "Superlative"]


def test_noun_collapses_gender_dimension():
    """Library may tag the same noun's forms with different genders
    (Masc/Neut/Common); the noun layout should produce a single
    Case × Number grid, no gender columns."""
    forms = [
        {"form": "vir", "upos": "NOUN",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "viri", "upos": "NOUN",
         "feats": {"Case": "Nom", "Number": "Plur", "Gender": "Com"}},
        {"form": "vira", "upos": "NOUN",
         "feats": {"Case": "Nom", "Number": "Plur", "Gender": "Neut"}},
    ]
    out = layout_paradigm(forms, "NOUN")
    decl = out["blocks"][0]["decl"]
    assert decl["genders"] is None  # collapsed
    assert decl["cells"][("Nom", "Plur", "")] == ["viri", "vira"]
