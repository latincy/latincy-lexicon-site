"""Bucketing logic for paradigm rendering — sanity-check the shape of
layout dicts the template renders against."""

from latincy_lexicon_site.paradigm_layout import layout_paradigm


def _form(form, **feats):
    alternate = feats.pop("alternate", False)
    upos = feats.pop("upos", "VERB")
    return {"form": form, "upos": upos, "feats": feats, "alternate": alternate}


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


def test_verb_reclassifies_future_perfect_by_aspect():
    """The library tags both ``amabo`` (Future) and ``amavero`` (Future
    Perfect) as Tense=Fut, distinguishing them with Aspect=Perf on the
    future perfect. The layout maps Tense=Fut|Aspect=Perf to its FutP row."""
    forms = [
        _form("amabo", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("amavero", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Aspect="Perf", Voice="Act", Person="1", Number="Sing"),
    ]
    out = layout_paradigm(forms, "VERB")
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    tenses = {r["tense"] for r in ind["rows"]}
    assert "Fut" in tenses and "FutP" in tenses
    fut_row = next(r for r in ind["rows"] if r["tense"] == "Fut")
    futp_row = next(r for r in ind["rows"] if r["tense"] == "FutP")
    fut_cells = [x for grid in fut_row["voices"].values() for sub in grid for c in sub for x in c]
    futp_cells = [x for grid in futp_row["voices"].values() for sub in grid for c in sub for x in c]
    assert "amabo" in fut_cells and "amabo" not in futp_cells
    assert "amavero" in futp_cells and "amavero" not in fut_cells


def test_verb_routes_flagged_forms_to_alternates():
    """Non-canonical forms arrive flagged ``alternate`` by the library
    (Plautine ``amasso``/``amassi`` off the syncopated stem). The layout
    routes any flagged form to alternates and keeps the canonical ones in
    their cells."""
    forms = [
        _form("amabo", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("amasso", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing", alternate=True),
        _form("amavi", VerbForm="Fin", Mood="Ind", Tense="Past",
              Voice="Act", Person="1", Number="Sing"),
        _form("amassi", VerbForm="Fin", Mood="Ind", Tense="Past",
              Voice="Act", Person="1", Number="Sing", alternate=True),
    ]
    out = layout_paradigm(forms, "VERB")
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "amasso" in alt_forms and "amassi" in alt_forms
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    fut_row = next(r for r in ind["rows"] if r["tense"] == "Fut")
    fut_cells = [x for grid in fut_row["voices"].values() for sub in grid for c in sub for x in c]
    assert "amabo" in fut_cells and "amasso" not in fut_cells


def test_verb_keeps_irregular_future_in_cell():
    """``sum``'s canonical Future 1sg is ``ero`` (Tense=Fut, no Aspect) —
    it stays in the Future row, while ``fuero`` (Aspect=Perf) is the Future
    Perfect. Aspect, not the ending, drives the split."""
    forms = [
        _form("ero", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Voice="Act", Person="1", Number="Sing"),
        _form("fuero", VerbForm="Fin", Mood="Ind", Tense="Fut",
              Aspect="Perf", Voice="Act", Person="1", Number="Sing"),
    ]
    out = layout_paradigm(forms, "VERB")
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


def _inf(form, voice="Act", tense="Pres", alternate=False):
    return {"form": form, "upos": "VERB", "alternate": alternate, "feats": {
        "VerbForm": "Inf", "Tense": tense, "Voice": voice}}


def test_verb_routes_archaic_and_bogus_infinitives_to_alternates():
    """Non-canonical infinitives arrive flagged by the library (archaic
    ``amarier``, bogus ``ame``, syncopated ``amasse``); the layout keeps
    only the canonical ones in the infinitive cells."""
    forms = [
        _inf("amare", "Act"),     # canonical
        _inf("ame", "Act", alternate=True),       # bogus
        _inf("amari", "Pass"),    # canonical
        _inf("amarier", "Pass", alternate=True),  # archaic
        _inf("amavisse", "Act", tense="Past"),  # canonical perfect
        _inf("amasse", "Act", tense="Past", alternate=True),  # syncopated
    ]
    out = layout_paradigm(forms, "VERB")
    inf_block = next(b for b in out["blocks"] if b["title"] == "Infinitives")
    rows_by_label = {r["label"]: r["forms"] for r in inf_block["rows"]}
    assert rows_by_label.get("Present Active") == ["amare"]
    assert rows_by_label.get("Present Passive") == ["amari"]
    assert rows_by_label.get("Perfect Active") == ["amavisse"]
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "ame" in alt_forms
    assert "amarier" in alt_forms
    assert "amasse" in alt_forms


def _ppp_form(form, alternate=False, **feats):
    feats = {**feats, "VerbForm": "Part", "Tense": "Past", "Voice": "Pass",
             "Aspect": "Perf"}
    return {"form": form, "upos": "VERB", "alternate": alternate, "feats": feats}


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


def test_verb_routes_flagged_present_system_artefact_to_alternates():
    """Wrong-stem/wrong-conj present artefacts (e.g. audio's ``audbam``)
    arrive flagged by the library; a flagged finite present form is routed
    to alternates while the canonical cell form stays."""
    forms = [
        _form("audiebam", VerbForm="Fin", Mood="Ind", Tense="Imp",
              Voice="Act", Person="1", Number="Sing"),
        _form("audbam", VerbForm="Fin", Mood="Ind", Tense="Imp",
              Voice="Act", Person="1", Number="Sing", alternate=True),
    ]
    out = layout_paradigm(forms, "VERB")
    ind = next(b for b in out["blocks"] if b["title"] == "Indicative")
    imp = next(r for r in ind["rows"] if r["tense"] == "Imp")
    cells = [x for grid in imp["voices"].values() for sub in grid for c in sub for x in c]
    assert "audiebam" in cells and "audbam" not in cells
    assert "audbam" in {a["form"] for a in out["alternates"]}


def test_verb_routes_flagged_participles_to_alternates():
    """Wrong-stem participles arrive flagged by the library; the layout
    routes the flagged ones (``dicans``, ``dicatus``) to alternates and
    keeps the canonical ones (``dicens``, ``dictus``) in the participle
    blocks."""
    forms = [
        {"form": "dicens", "upos": "VERB", "alternate": False, "feats": {
            "VerbForm": "Part", "Tense": "Pres", "Voice": "Act",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "dicans", "upos": "VERB", "alternate": True, "feats": {
            "VerbForm": "Part", "Tense": "Pres", "Voice": "Act",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "dictus", "upos": "VERB", "alternate": False, "feats": {
            "VerbForm": "Part", "Tense": "Past", "Voice": "Pass",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
        {"form": "dicatus", "upos": "VERB", "alternate": True, "feats": {
            "VerbForm": "Part", "Tense": "Past", "Voice": "Pass",
            "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
    ]
    out = layout_paradigm(forms, "VERB")
    alt_forms = {a["form"] for a in out["alternates"]}
    assert "dicans" in alt_forms and "dicatus" in alt_forms
    # The kept participles render in their own decl blocks
    pap = next(b for b in out["blocks"] if b["kind"] == "participles")
    pres_act = next(r for r in pap["rows"] if r["label"] == "Present Active")
    nom_masc = pres_act["decl"]["cells"].get(("Nom", "Sing", "Masc"))
    assert nom_masc == ["dicens"]


def test_verb_drops_spurious_perfect_passive_participle_for_irregular():
    """The library flags sum's mechanically-declined fake PPP
    (``futus, futa, futum``) as alternate while keeping the real future
    active participle (``futurus``). The layout routes the flagged PPP to
    alternates, so no Perfect Passive participle block appears."""
    forms = [
        _form("sum", VerbForm="Fin", Mood="Ind", Tense="Pres",
              Voice="Act", Person="1", Number="Sing"),
        _ppp_form("futus", alternate=True, Case="Nom", Number="Sing", Gender="Masc"),
        {"form": "futurus", "upos": "VERB", "alternate": False,
         "feats": {"VerbForm": "Part", "Tense": "Fut", "Voice": "Act",
                   "Case": "Nom", "Number": "Sing", "Gender": "Masc"}},
    ]
    out = layout_paradigm(forms, "VERB")
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


def test_other_layout_drops_spurious_adv_degrees_when_form_unchanged():
    """The lexicon emits Pos/Cmp/Sup degree forms for every ADV reading,
    but indeclinables like `cum` don't actually inflect — the Cmp/Sup
    rows have the same surface as the bare/Pos row. Drop them so the
    user doesn't see three identical 'cum (Cmp)' / 'cum (Sup)' rows for
    a non-comparable adverb. A real adverb like *celeriter* keeps all
    three because its degrees have different surfaces."""
    forms = [
        {"form": "cum", "upos": "ADV", "feats": {}},
        {"form": "cum", "upos": "ADV", "feats": {"Degree": "Pos"}},
        {"form": "cum", "upos": "ADV", "feats": {"Degree": "Cmp"}},
        {"form": "cum", "upos": "ADV", "feats": {"Degree": "Sup"}},
    ]
    out = labels = layout_paradigm(forms, "ADV")
    rows = out["blocks"][0]["rows"]
    labels = [r["label"] for r in rows]
    assert not any("Cmp" in lbl for lbl in labels), (
        f"spurious Cmp row not dropped: {labels}"
    )
    assert not any("Sup" in lbl for lbl in labels), (
        f"spurious Sup row not dropped: {labels}"
    )


def test_other_layout_keeps_real_adv_degrees_when_forms_differ():
    """A genuinely comparable adverb (different surface per degree)
    keeps all three rows."""
    forms = [
        {"form": "celeriter", "upos": "ADV", "feats": {"Degree": "Pos"}},
        {"form": "celerius", "upos": "ADV", "feats": {"Degree": "Cmp"}},
        {"form": "celerrime", "upos": "ADV", "feats": {"Degree": "Sup"}},
    ]
    out = layout_paradigm(forms, "ADV")
    rows = out["blocks"][0]["rows"]
    assert len(rows) == 3
    forms_seen = {r["forms"][0] for r in rows}
    assert forms_seen == {"celeriter", "celerius", "celerrime"}


def test_other_layout_titles_block_indeclinable_when_one_surface():
    """When every surviving row shares the same surface form, the block
    is titled "Indeclinable" instead of the generic "Forms" — gives the
    user an at-a-glance signal that the word doesn't inflect."""
    forms = [
        {"form": "cum", "upos": "ADV", "feats": {}},
        {"form": "cum", "upos": "ADP", "feats": {"Case": "Gen"}},
        {"form": "cum", "upos": "ADP", "feats": {"Case": "Abl"}},
    ]
    out = layout_paradigm(forms, "ADV")
    assert out["blocks"][0]["title"] == "Indeclinable"


def test_other_layout_keeps_forms_title_when_surfaces_differ():
    """Multiple distinct surfaces -> title stays as 'Forms'."""
    forms = [
        {"form": "celeriter", "upos": "ADV", "feats": {"Degree": "Pos"}},
        {"form": "celerius", "upos": "ADV", "feats": {"Degree": "Cmp"}},
        {"form": "celerrime", "upos": "ADV", "feats": {"Degree": "Sup"}},
    ]
    out = layout_paradigm(forms, "ADV")
    assert out["blocks"][0]["title"] == "Forms"


def test_other_layout_drops_empty_forms_and_dedupes():
    """Indeclinables/closed-class words (e.g. `cum`) get the `other` layout.
    The library can synthesize empty-string forms and many duplicates of
    the same surface; the layout must drop empties and collapse rows that
    share the same (form, feats), so the user doesn't see eight blank
    `cum` rows or stray empty cells."""
    forms = [
        {"form": "cum", "upos": "ADV", "feats": {}},
        {"form": "", "upos": "ADV", "feats": {}},
        {"form": "cum", "upos": "ADV", "feats": {"Degree": "Pos"}},
        {"form": "cum", "upos": "ADV", "feats": {"Degree": "Pos"}},  # exact dupe
        {"form": "cum", "upos": "ADP", "feats": {"Case": "Abl"}},
        {"form": "cum", "upos": "ADP", "feats": {"Case": "Acc"}},
    ]
    out = layout_paradigm(forms, "ADV")
    rows = out["blocks"][0]["rows"]
    assert all(r["forms"] and r["forms"][0] for r in rows), (
        "no row should have an empty form"
    )
    # Exact (form, feats) duplicates collapse
    assert len(rows) == 4
    # Each row carries a label that surfaces upos / feats so the user can
    # tell ADV-Degree=Pos from ADP-Case=Abl readings of the same surface.
    labels = [r["label"] for r in rows]
    assert any("ADP" in lbl and "Abl" in lbl for lbl in labels)
    assert any("ADV" in lbl for lbl in labels)
