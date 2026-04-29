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


def test_verb_reclassifies_future_perfect_using_perfect_stem():
    """The library tags both ``amabo`` (Future) and ``amavero`` (Future
    Perfect) as Tense=Fut. When an entry is supplied, FutP forms should
    be split out into their own row by perfect-stem prefix."""
    forms = [
        _form("amabo", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("amavero", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
    ]
    entry = {"headword": "amo", "principal_parts": ["am", "am", "amass"]}
    out = layout_paradigm(forms, "VERB", entry)
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    tenses = {r["tense"] for r in ind["rows"]}
    assert "Fut" in tenses and "FutP" in tenses
    fut_row = next(r for r in ind["rows"] if r["tense"] == "Fut")
    futp_row = next(r for r in ind["rows"] if r["tense"] == "FutP")
    fut_cells = [x for grid in fut_row["voices"].values() for sub in grid for c in sub for x in c]
    futp_cells = [x for grid in futp_row["voices"].values() for sub in grid for c in sub for x in c]
    assert "amabo" in fut_cells and "amabo" not in futp_cells
    assert "amavero" in futp_cells and "amavero" not in fut_cells


def test_verb_routes_plautine_sigmatic_to_alternates():
    """Plautine ``amasso`` shares features with canonical ``amabo`` but
    uses a non-canonical stem; without entry stems we'd put both in the
    Future cell. With entry supplied, ``amasso`` moves to alternates."""
    forms = [
        _form("amabo", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("amasso", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("amavi", VerbForm="Fin", Mood="Ind", Tense="Past",
              Voice="Act", Person="1", Number="Sing"),
        _form("amassi", VerbForm="Fin", Mood="Ind", Tense="Past",
              Voice="Act", Person="1", Number="Sing"),
    ]
    entry = {"headword": "amo", "principal_parts": ["am", "am", "amass"]}
    out = layout_paradigm(forms, "VERB", entry)
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "amasso" in alt_forms and "amassi" in alt_forms
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    fut_row = next(r for r in ind["rows"] if r["tense"] == "Fut")
    fut_cells = [x for grid in fut_row["voices"].values() for sub in grid for c in sub for x in c]
    assert "amabo" in fut_cells and "amasso" not in fut_cells


def test_verb_keeps_irregular_future_in_cell():
    """``sum``'s canonical Future 1sg is ``ero`` — same ending as the
    Future Perfect rule keys on. The perfect-stem guard must keep it in
    the Future row, not promote it to Future Perfect."""
    forms = [
        _form("ero", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("fuero", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
    ]
    entry = {"headword": "sum", "principal_parts": ["s", "fu", "fut"]}
    out = layout_paradigm(forms, "VERB", entry)
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    fut_row = next(r for r in ind["rows"] if r["tense"] == "Fut")
    futp_row = next(r for r in ind["rows"] if r["tense"] == "FutP")
    fut_cells = [x for grid in fut_row["voices"].values() for sub in grid for c in sub for x in c]
    futp_cells = [x for grid in futp_row["voices"].values() for sub in grid for c in sub for x in c]
    assert "ero" in fut_cells and "fuero" in futp_cells


def test_verb_layout_is_nooperatively_safe_without_entry():
    """The entry arg is optional. When absent, no stem-based routing
    fires and Plautine forms stay in-cell next to canonical ones."""
    forms = [
        _form("amabo", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("amasso", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
    ]
    out = layout_paradigm(forms, "VERB")
    assert out["alternates"] == []
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    fut_row = next(r for r in ind["rows"] if r["tense"] == "Fut")
    fut_cells = [x for grid in fut_row["voices"].values() for sub in grid for c in sub for x in c]
    assert "amasso" in fut_cells and "amabo" in fut_cells


def _inf(form, voice="Act", tense="Pres"):
    return {"form": form, "upos": "VERB", "feats": {
        "VerbForm": "Inf", "Tense": tense, "Voice": voice}}


def test_verb_routes_archaic_and_bogus_infinitives_to_alternates():
    """Archaic ``amarier`` and library-bogus ``ame`` should not appear
    in the canonical Present Passive / Active infinitive cells."""
    forms = [
        _inf("amare", "Act"),     # canonical
        _inf("ame", "Act"),       # bogus — must end in -re
        _inf("amari", "Pass"),    # canonical
        _inf("amarier", "Pass"),  # archaic — must end in -ri or -i
        _inf("amavisse", "Act", tense="Past"),  # canonical perfect
        _inf("amasse", "Act", tense="Past"),    # syncopated/Plautine
    ]
    entry = {"headword": "amo", "principal_parts": ["am", "am", "amass"]}
    out = layout_paradigm(forms, "VERB", entry)
    inf_block = next(b for b in out["blocks"] if b["title"] == "Infinitives")
    rows_by_label = {r["label"]: r["forms"] for r in inf_block["rows"]}
    assert rows_by_label.get("Present Active") == ["amare"]
    assert rows_by_label.get("Present Passive") == ["amari"]
    assert rows_by_label.get("Perfect Active") == ["amavisse"]
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "ame" in alt_forms
    assert "amarier" in alt_forms
    assert "amasse" in alt_forms


def _ppp_form(form, **feats):
    feats = {**feats, "VerbForm": "Part", "Tense": "Past", "Voice": "Pass",
             "Aspect": "Perf"}
    return {"form": form, "upos": "VERB", "feats": feats}


def test_verb_synthesizes_periphrastic_perfect_passive():
    """Latin's perfect-system passive is multi-word (``amatus sum``) and
    the library doesn't emit it as finite forms. When the verb has a
    real PPP, layout should synthesize textbook periphrastic forms."""
    forms = [
        _form("amavi", VerbForm="Fin", Mood="Ind", Tense="Past",
              Voice="Act", Person="1", Number="Sing"),
        _ppp_form("amatus", Case="Nom", Number="Sing", Gender="Masc"),
        _ppp_form("amati", Case="Nom", Number="Plur", Gender="Masc"),
    ]
    entry = {"headword": "amo", "principal_parts": ["am", "am", "amass"]}
    out = layout_paradigm(forms, "VERB", entry)
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    past_row = next(r for r in ind["rows"] if r["tense"] == "Past")
    pass_grid = past_row["voices"].get("Pass")
    assert pass_grid is not None
    # Sing: amatus sum/es/est, Plur: amati sumus/estis/sunt
    assert pass_grid[0][0] == ["amatus sum"]
    assert pass_grid[0][2] == ["amatus est"]
    assert pass_grid[1][0] == ["amati sumus"]
    assert pass_grid[1][2] == ["amati sunt"]


def test_verb_periphrastic_synthesis_does_not_introduce_phantom_row():
    """Periphrastic synthesis must not create a Pst/Past phantom row
    whose Active column is empty. If the verb has no Active forms for
    a tense, the synthesized Passive row would surface a row of dashes
    in Active — skip synthesis in that case."""
    forms = [
        _form("amo", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
        _ppp_form("amatus", Case="Nom", Number="Sing", Gender="Masc"),
        _ppp_form("amati", Case="Nom", Number="Plur", Gender="Masc"),
    ]
    entry = {"headword": "amo", "principal_parts": ["am", "am", "amass"]}
    out = layout_paradigm(forms, "VERB", entry)
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    tenses = [r["tense"] for r in ind["rows"]]
    # No Past/Pst row at all because the input has no Past Active form
    assert "Past" not in tenses
    assert "Pst" not in tenses


def test_verb_filters_wrong_conj_present_system_forms():
    """The library can lump a 1st-conj homonym's forms into a 3rd-conj
    headword's paradigm (e.g. dico = dicere AND dicare). For a 3rd-conj
    entry, ``dicas`` (1st-conj Pres Ind Act 2sg) must NOT appear in the
    Pres Ind Act 2sg cell — only ``dicis`` (the canonical 3rd-conj form)
    belongs there. Bare-stem ``reg`` and wrong-stem ``audbam`` get
    filtered the same way."""
    forms = [
        _form("dico", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
        _form("dicis", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="2", Number="Sing"),
        _form("dicas", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="2", Number="Sing"),  # 1st-conj intruder
    ]
    entry = {"headword": "dico", "principal_parts": ["dic", "dic", "dix", "dict"]}
    out = layout_paradigm(forms, "VERB", entry)
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    pres = next(r for r in ind["rows"] if r["tense"] == "Pres")
    cells = [x for grid in pres["voices"].values() for sub in grid for c in sub for x in c]
    assert "dicis" in cells and "dicas" not in cells
    assert "dicas" in {a["form"] for a in out["alternates"]}


def test_verb_filters_wrong_stem_participles():
    """Same homonym problem for participles: a 3rd-conj entry must not
    pick up 1st-conj ``dicans`` (Pres Act), ``dicaturus`` (Fut Act),
    ``dicandus`` (gerundive), or ``dicatus`` (PPP)."""
    forms = [
        {"form": "dicens", "upos": "VERB", "feats": {
            "VerbForm": "Part", "Tense": "Pres", "Voice": "Act",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "dicans", "upos": "VERB", "feats": {
            "VerbForm": "Part", "Tense": "Pres", "Voice": "Act",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "dictus", "upos": "VERB", "feats": {
            "VerbForm": "Part", "Tense": "Past", "Voice": "Pass",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "dicatus", "upos": "VERB", "feats": {
            "VerbForm": "Part", "Tense": "Past", "Voice": "Pass",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
    ]
    entry = {"headword": "dico", "principal_parts": ["dic", "dic", "dix", "dict"]}
    out = layout_paradigm(forms, "VERB", entry)
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "dicans" in alt_forms and "dicatus" in alt_forms
    # The kept participles render in their own decl blocks
    pap = next(b for b in out["blocks"] if b["kind"] == "participles")
    pres_act = next(r for r in pap["rows"] if r["label"] == "Present Active")
    nom_masc = pres_act["decl"]["cells"].get(("Nom", "Sing", "Masc"))
    assert nom_masc == ["dicens"]


def test_verb_drops_spurious_perfect_passive_participle_for_irregular():
    """Library generates a Perfect Passive participle for sum
    (``futus, futa, futum``) by mechanically declining the supine stem,
    even though Latin's sum has no such participle. The 3-stem layout
    [pres, perf, sup] flags the verb as having no real PPP, and those
    forms get routed to alternates."""
    forms = [
        _form("sum", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
        _ppp_form("futus", Case="Nom", Number="Sing", Gender="Masc"),
        {"form": "futurus", "upos": "VERB",
         "feats": {"VerbForm": "Part", "Tense": "Fut", "Voice": "Act",
                   "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
    ]
    entry = {"headword": "sum", "principal_parts": ["s", "fu", "fut"]}
    out = layout_paradigm(forms, "VERB", entry)
    titles = [r["label"] for b in out["blocks"] if b["kind"] == "participles"
              for r in b["rows"]]
    assert "Future Active" in titles
    assert "Perfect Passive" not in titles
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "futus" in alt_forms


def test_adj_splats_genderless_dat_abl_plural():
    """Latin adj Dat/Abl Plur (e.g. ``bonis``) is syncretic across
    Masc/Fem/Neut. Library tags those forms gender-less; the layout
    should propagate them into each gender column so the per-gender
    table renders them, not drop them."""
    forms = [
        {"form": "bonus", "upos": "ADJ",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Masc",
                   "Degree": "Pos"}},
        {"form": "bona", "upos": "ADJ",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Fem",
                   "Degree": "Pos"}},
        {"form": "bonum", "upos": "ADJ",
         "feats": {"Case": "Nom", "Number": "Sing", "Gender": "Neut",
                   "Degree": "Pos"}},
        {"form": "bonis", "upos": "ADJ",
         "feats": {"Case": "Dat", "Number": "Plur", "Degree": "Pos"}},
    ]
    out = layout_paradigm(forms, "ADJ")
    decl = out["blocks"][0]["decl"]
    assert decl["genders"] == ["Masc", "Fem", "Neut"]
    for g in decl["genders"]:
        assert decl["cells"].get(("Dat", "Plur", g)) == ["bonis"]


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
