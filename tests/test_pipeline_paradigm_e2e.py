"""End-to-end checks: URL slug → resolved paradigm.

Locks in slug→lemma resolution, multi-paradigm splitting for homonyms,
and the empty/closed-class graceful path. Covers cases users actually
type that have historically broken.
"""

from __future__ import annotations

import pytest
from spacy.language import Language

from latincy_lexicon_site.pipeline import analyze_paradigm_sync, load_pipeline


@pytest.fixture(scope="module")
def nlp() -> Language:
    return load_pipeline("la_core_web_sm")


@pytest.fixture(scope="module")
def nlp_lg() -> Language:
    """Larger model — used to surface tagger-context bugs that sm hides.

    Both sm and lg register a ``trf_vectors`` factory; loading the second
    one in the same process raises ``ValueError [E004]``. Skip rather than
    fail when that happens — the lg-only test is best run in isolation
    (e.g. ``pytest tests/test_pipeline_paradigm_e2e.py -k lg``).
    """
    try:
        return load_pipeline("la_core_web_lg")
    except OSError:
        pytest.skip("la_core_web_lg not installed")
    except ValueError as exc:
        if "E004" in str(exc):
            pytest.skip(
                "la_core_web_lg conflicts with sm in same process; "
                "run lg test in isolation"
            )
        raise


def _ud_pos_set(paradigm: dict) -> set[str]:
    entry = paradigm.get("entry") or {}
    return set(entry.get("ud_pos") or [])


def test_inflected_slug_resolves_to_lemma(nlp: Language):
    """`/paradigm/amat` titles the page with `amo` and remembers the query."""
    r = analyze_paradigm_sync(nlp, "amat")
    assert r["lemma"] == "amo"
    assert r["query"] == "amat"
    assert len(r["paradigms"]) == 1
    assert len(r["paradigms"][0]["forms"]) > 200


def test_lemma_slug_renders(nlp: Language):
    """`/paradigm/amo` (slug already a lemma) emits the same paradigm."""
    r = analyze_paradigm_sync(nlp, "amo")
    assert r["lemma"] == "amo"
    assert r["query"] == "amo"
    assert len(r["paradigms"]) == 1
    assert len(r["paradigms"][0]["forms"]) > 200


@pytest.mark.parametrize("slug", ["dico", "dices"])
def test_homonym_verbs_split_by_principal_parts(nlp: Language, slug: str):
    """`dico` is both *dicere* (3rd, 'say') and *dicare* (1st, 'dedicate').
    Each gets its own paradigm group with distinct principal parts."""
    r = analyze_paradigm_sync(nlp, slug)
    assert r["lemma"] == "dico"
    assert len(r["paradigms"]) >= 2
    pp_keys = {tuple((p["entry"] or {}).get("principal_parts") or ()) for p in r["paradigms"]}
    assert len(pp_keys) >= 2, f"expected distinct principal_parts, got {pp_keys}"
    for p in r["paradigms"]:
        assert len(p["forms"]) > 0
        assert "VERB" in _ud_pos_set(p)


def test_noun_inflected_slug_resolves(nlp: Language):
    """Unambiguous noun form: `curae` → lemma `cura` with noun paradigm."""
    r = analyze_paradigm_sync(nlp, "curae")
    assert r["lemma"] == "cura"
    assert len(r["paradigms"]) >= 1
    assert any("NOUN" in _ud_pos_set(p) and len(p["forms"]) > 0 for p in r["paradigms"])


def test_noun_lemma_slug_emits_noun_paradigm(nlp: Language):
    """Bare lemma `cura` should still surface a noun paradigm with forms.

    The slug is genuinely ambiguous (noun *cura, -ae* vs imperative of *curo*).
    Whichever POS the tagger picks, at least the noun reading must produce
    forms — otherwise the page renders empty for a user who typed a plain
    dictionary headword.
    """
    r = analyze_paradigm_sync(nlp, "cura")
    assert r["lemma"] == "cura"
    noun_paradigms = [p for p in r["paradigms"] if "NOUN" in _ud_pos_set(p)]
    assert noun_paradigms, "no NOUN paradigm produced for `cura`"
    assert any(len(p["forms"]) > 0 for p in noun_paradigms), (
        "NOUN paradigm for `cura` has zero forms"
    )


def test_noun_lemma_slug_emits_noun_paradigm_lg(nlp_lg: Language):
    """Same as above on the lg model. lg's tagger picks VERB for bare
    `cura` out of context, so the spaCy component generates 0 forms; the
    pipeline falls back to an unfiltered generator call against the
    resolved lemma so the noun reading still surfaces."""
    r = analyze_paradigm_sync(nlp_lg, "cura")
    assert r["lemma"] == "cura"
    noun_paradigms = [p for p in r["paradigms"] if "NOUN" in _ud_pos_set(p)]
    assert noun_paradigms, "no NOUN paradigm produced for `cura`"
    assert any(len(p["forms"]) > 0 for p in noun_paradigms)


def test_adjective_lemma_emits_paradigm(nlp: Language):
    """`bonus` is both an adjective and (substantive) noun in the lexicon."""
    r = analyze_paradigm_sync(nlp, "bonus")
    assert r["lemma"] == "bonus"
    assert len(r["paradigms"]) >= 1
    adj_paradigms = [p for p in r["paradigms"] if "ADJ" in _ud_pos_set(p)]
    assert adj_paradigms, "no ADJ paradigm for `bonus`"
    assert any(len(p["forms"]) >= 80 for p in adj_paradigms)


def test_closed_class_word_does_not_crash(nlp: Language):
    """`et` is a coordinating conjunction — no inflectional paradigm to render,
    but the route must return cleanly (1 paradigm, ≤1 form, no exception)."""
    r = analyze_paradigm_sync(nlp, "et")
    assert r["lemma"] == "et"
    assert isinstance(r["paradigms"], list)
    for p in r["paradigms"]:
        assert len(p["forms"]) <= 1


def test_unknown_token_returns_empty_paradigms(nlp: Language):
    """A slug that doesn't lemmatize to anything known should yield an empty
    or placeholder paradigm list — never raise."""
    r = analyze_paradigm_sync(nlp, "xyzabc123")
    assert "paradigms" in r
    assert isinstance(r["paradigms"], list)


def test_noun_forms_carry_entry_gender_not_com(nlp: Language):
    """The library's 1st-decl inflection rule is gender-agnostic and emits
    ``Gender=Com``; the entry's recorded gender (F for *cura*) is more
    specific and what a learner expects to see ("feminine"). When all
    NOUN entries for a lemma agree on M/F/N, NOUN forms should carry
    that gender instead of ``Com``."""
    r = analyze_paradigm_sync(nlp, "cura")
    noun_paradigms = [
        p for p in r["paradigms"] if "NOUN" in (
            (p.get("entry") or {}).get("ud_pos") or []
        )
    ]
    assert noun_paradigms
    forms = noun_paradigms[0]["forms"]
    assert forms, "expected noun forms for cura"
    genders = {f["feats"].get("Gender") for f in forms if f["feats"].get("Gender")}
    assert "Com" not in genders, f"expected Com to be replaced, got {genders}"
    assert "Fem" in genders, f"expected Fem in {genders}"


def test_indeclinable_collapses_byte_identical_paradigms(nlp: Language):
    """`cum` has lexicon entries under multiple principal-parts groups
    (CCONJ/PART/SCONJ vs ADV) but the generated form-set is the same
    object for both. The user should see one paradigm, not two
    byte-identical tables. Verbs are exempt from this collapse since
    per-conj layout filtering can render distinct tables from a shared
    forms list."""
    r = analyze_paradigm_sync(nlp, "cum")
    assert len(r["paradigms"]) == 1, (
        f"expected 1 paradigm for indeclinable `cum`, got {len(r['paradigms'])}"
    )
