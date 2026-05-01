"""Textbook gloss for UD morph feats — keeps the paradigm intro readable
('3rd person singular present indicative active' instead of
'Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act')."""

from latincy_lexicon_site.morph_gloss import morph_to_textbook


def test_finite_verb():
    assert morph_to_textbook({
        "VerbForm": "Fin", "Person": "3", "Number": "Sing",
        "Tense": "Pres", "Mood": "Ind", "Voice": "Act",
    }) == "3rd person singular present indicative active"


def test_finite_verb_perfect_passive_subjunctive():
    assert morph_to_textbook({
        "VerbForm": "Fin", "Person": "1", "Number": "Plur",
        "Tense": "Past", "Mood": "Sub", "Voice": "Pass",
    }) == "1st person plural perfect subjunctive passive"


def test_infinitive():
    assert morph_to_textbook({
        "VerbForm": "Inf", "Tense": "Pres", "Voice": "Act",
    }) == "present active infinitive"


def test_participle():
    """Participles carry case/number/gender on top of tense+voice."""
    assert morph_to_textbook({
        "VerbForm": "Part", "Tense": "Pres", "Voice": "Act",
        "Case": "Gen", "Number": "Sing", "Gender": "Masc",
    }) == "present active participle genitive singular masculine"


def test_noun_dat_sing_fem():
    assert morph_to_textbook({
        "Case": "Dat", "Number": "Sing", "Gender": "Fem",
    }) == "dative singular feminine"


def test_adjective_with_degree():
    assert morph_to_textbook({
        "Case": "Acc", "Number": "Plur", "Gender": "Neut",
        "Degree": "Cmp",
    }) == "accusative plural neuter comparative"


def test_empty_feats_returns_empty_string():
    assert morph_to_textbook({}) == ""
    assert morph_to_textbook(None) == ""


def test_unknown_feat_values_are_skipped():
    """A feat value the table doesn't know about (e.g. a model glitch)
    drops out of the gloss instead of breaking it."""
    assert morph_to_textbook({
        "VerbForm": "Fin", "Person": "3", "Number": "Sing",
        "Tense": "Bogus", "Mood": "Ind", "Voice": "Act",
    }) == "3rd person singular indicative active"
