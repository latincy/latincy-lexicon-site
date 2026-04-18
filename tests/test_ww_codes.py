from latincy_lexicon_site.ww_codes import ww_age, ww_area, ww_freq, ww_geo, ww_source


def test_ww_age_expands_X_to_all_eras():
    assert ww_age("X") == "all eras"


def test_ww_age_expands_C_to_classical():
    assert ww_age("C") == "Classical (80 BC – 17 AD)"


def test_ww_age_unknown_code_returns_raw():
    assert ww_age("Z") == "Z"


def test_ww_age_empty_returns_empty():
    assert ww_age("") == ""


def test_ww_age_none_returns_empty():
    assert ww_age(None) == ""


def test_ww_freq_A_is_very_frequent():
    assert ww_freq("A") == "very frequent"


def test_ww_freq_X_is_unknown():
    assert ww_freq("X") == "unknown frequency"


def test_ww_area_W_is_military():
    assert ww_area("W") == "military"


def test_ww_area_X_is_all_domains():
    assert ww_area("X") == "all domains"


def test_ww_geo_I_is_italy():
    assert ww_geo("I") == "Italy / Rome"


def test_ww_geo_X_is_all_regions():
    assert ww_geo("X") == "all regions"


def test_ww_source_O_is_oxford_latin_dict():
    assert ww_source("O") == "Oxford Latin Dictionary"
