from latincy_lexicon_site.pos_labels import pos_label


def test_noun_code_stays_noun():
    assert pos_label("N") == "noun"


def test_verb_code_stays_verb():
    assert pos_label("V") == "verb"


def test_adj_is_adjective():
    assert pos_label("ADJ") == "adjective"


def test_adv_is_adverb():
    assert pos_label("ADV") == "adverb"


def test_pron_is_pronoun():
    assert pos_label("PRON") == "pronoun"


def test_prep_is_preposition():
    assert pos_label("PREP") == "preposition"


def test_conj_is_conjunction():
    assert pos_label("CONJ") == "conjunction"


def test_interj_is_interjection():
    assert pos_label("INTERJ") == "interjection"


def test_num_is_numeral():
    assert pos_label("NUM") == "numeral"


def test_tackon_is_enclitic():
    assert pos_label("TACKON") == "enclitic"


def test_packon_is_part_of_compound():
    assert pos_label("PACKON") == "part of compound"


def test_prefix_and_suffix():
    assert pos_label("PREFIX") == "prefix"
    assert pos_label("SUFFIX") == "suffix"


def test_unknown_code_returns_raw():
    assert pos_label("XYZ") == "XYZ"


def test_empty_returns_empty():
    assert pos_label("") == ""


def test_none_returns_empty():
    assert pos_label(None) == ""
