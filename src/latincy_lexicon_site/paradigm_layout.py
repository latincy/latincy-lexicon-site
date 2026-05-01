"""Bucket a flat list of inflected forms into a textbook-style layout.

The library's paradigm generator emits one row per form with UD features
attached. Rendering them flat is unreadable — even a single 1st-conj
verb produces ~200+ rows. This module groups them into the sectioned
shape a Latin grammar would print:

- **Verbs** — Indicative / Subjunctive / Imperative blocks with each
  Tense as a row × Person×Number as columns, Active and Passive paired.
  Non-finite forms (Infinitives, Participles, Supines, Gerunds) live in
  separate sections.
- **Adjectives** — Positive / Comparative / Superlative blocks; each
  is a Gender × Case × Number table.
- **Nouns** — Case × Number table with Gender as a header annotation.

Forms whose features don't fit a standard cell are collected into an
``alternates`` list rendered as an expandable section. This catches
e.g. Plautine sigmatic future forms (``amasso, amassero``) that share
features with the standard future indicative but use a different stem;
v1 keeps them in the cell next to the canonical form rather than
trying to disambiguate.
"""

from __future__ import annotations

from typing import Any

# Display order for tense rows within a (mood, voice) block. Canonical
# Latin order: present-system (Pres/Imp/Fut), then perfect-system
# (Past=Perfect, Pqp=Pluperfect, FutP=Future Perfect). ``Pst`` is a UD
# alias the library accepts but doesn't actually emit; left out so it
# can't introduce a phantom row.
_VERB_TENSE_ORDER = ["Pres", "Imp", "Fut", "Past", "Pqp", "FutP"]
_VERB_MOOD_ORDER = ["Ind", "Sub", "Imp"]
_VERB_VOICE_ORDER = ["Act", "Pass"]
_PERSONS = ["1", "2", "3"]
_NUMBERS = ["Sing", "Plur"]

_NOUN_CASE_ORDER = ["Nom", "Gen", "Dat", "Acc", "Abl", "Voc", "Loc"]
_GENDER_ORDER = ["Masc", "Fem", "Neut", "Com"]
_DEGREE_ORDER = ["Pos", "Cmp", "Sup"]

# Future-perfect indicative endings (Active). Used to disambiguate the
# library's collapsed Tense=Fut bucket — both `amabo` (canonical Future)
# and `amavero` (canonical Future Perfect) come back tagged Tense=Fut.
# A form starting with the perfect stem AND ending in one of these is a
# Future Perfect; bare ending match alone would mis-grab `sum`'s `ero`.
_FUT_PERF_ENDINGS = (
    "erimus", "eritis", "erint", "erunt",
    "erim", "eris", "erit", "ero", "ere",
)

# Tenses that build off the perfect stem. Forms tagged with one of these
# but NOT starting with the canonical perfect stem are non-canonical
# (Plautine sigmatic etc.) and routed to alternates.
_PERF_SYS_TENSES = {"Past", "Pst", "Pqp", "FutP"}


def layout_paradigm(
    forms: list[dict],
    upos: str | None,
    entry: dict | None = None,
) -> dict[str, Any]:
    """Return a structured layout suitable for paradigm.html rendering.

    ``entry`` is the lexicon entry for the lemma; verb layout uses its
    principal-parts stems to route non-canonical forms (e.g. Plautine
    sigmatic ``amasso``) into the alternates section. Adj/noun layouts
    don't use it today.

    Top-level keys:
      - kind: "verb" | "adj" | "noun" | "other"
      - blocks: ordered list of section dicts (see _layout_* helpers)
      - alternates: leftover forms not bucketed into any block
      - total: total forms supplied (for the count line)
    """
    if not forms:
        return {"kind": "empty", "blocks": [], "alternates": [], "total": 0}

    # Use the upos arg if given, else infer from the first form (route may
    # leave upos unset on the response).
    kind_upos = upos or forms[0].get("upos") or ""
    if kind_upos == "VERB" or kind_upos == "AUX":
        return _layout_verb(forms, entry)
    if kind_upos == "ADJ":
        return _layout_adj(forms)
    if kind_upos in {"NOUN", "PROPN"}:
        return _layout_noun(forms)
    return _layout_other(forms)


# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------


def _layout_verb(forms: list[dict], entry: dict | None = None) -> dict[str, Any]:
    pres_stem, perf_stem, conj, has_real_ppp, sup_stem = _verb_stems(entry)

    finite: dict[tuple[str, str, str], dict[tuple[str, str], list[str]]] = {}
    infinitives: dict[tuple[str, str], list[str]] = {}
    participles: dict[tuple[str, str], list[dict]] = {}
    gerunds: list[dict] = []
    supines: list[dict] = []
    alternates: list[dict] = []

    for f in forms:
        feats = f.get("feats") or {}
        vf = feats.get("VerbForm")
        form = f.get("form")
        if not form:
            continue

        if vf == "Fin":
            _route_finite(f, form, feats, pres_stem, perf_stem, conj, finite, alternates)
        elif vf == "Inf":
            tense = feats.get("Tense", "Pres")
            voice = feats.get("Voice", "Act")
            if _is_inf_alternate(form, tense, voice, perf_stem):
                alternates.append(_alt(f))
                continue
            infinitives.setdefault((tense, voice), []).append(form)
        elif vf == "Part":
            tense = feats.get("Tense", "Pres")
            voice = feats.get("Voice", "Act")
            # Suppress the spurious "Perfect Passive" participle that the
            # library generates for verbs without a real one (e.g. sum's
            # `futus, futa, futum...` mechanically declined from the supine).
            if (
                tense == "Past"
                and voice == "Pass"
                and entry is not None
                and not has_real_ppp
            ):
                alternates.append(_alt(f))
                continue
            # Filter participles built from the wrong stem — for homonyms
            # like dico (dicere vs dicare), the library emits both
            # dicens/dicans (Pres Act), dicturus/dicaturus (Fut Act), etc.
            if _is_part_alternate(form, tense, voice, conj, pres_stem, sup_stem):
                alternates.append(_alt(f))
                continue
            participles.setdefault((tense, voice), []).append({
                "form": form,
                "case": feats.get("Case", ""),
                "number": feats.get("Number", ""),
                "gender": feats.get("Gender", ""),
            })
        elif vf == "Ger":
            gerunds.append({
                "form": form,
                "case": feats.get("Case", ""),
                "number": feats.get("Number", ""),
            })
        elif vf == "Sup":
            supines.append({
                "form": form,
                "case": feats.get("Case", ""),
            })
        else:
            alternates.append(_alt(f))

    # Synthesize periphrastic perfect-system passives (amatus sum,
    # amatus eram, amatus ero, amatus sim, amatus essem) when the verb
    # has a real PPP and the library hasn't emitted finite passive forms
    # for those tenses (it doesn't — they're multi-word in Latin).
    if has_real_ppp:
        _synth_periphrastic_passive(finite, participles)

    # The library doesn't tag gerunds (VerbForm=Ger). The gerund forms
    # `amandi/amando/amandum/amando` ARE the FPP's Neut Sing Gen/Dat/
    # Acc/Abl, so synthesize the block from the FPP data.
    _synth_gerund(gerunds, participles)

    # Multi-word infinitives (amaturum esse, amatum iri, amatum esse,
    # amatum fore, amaturum fuisse) aren't emitted by the library since
    # they're periphrastic. Build them from FAP / PPP / supine forms.
    _synth_multiword_infinitives(infinitives, participles, supines, has_real_ppp)

    blocks: list[dict] = []

    # Build finite blocks: one per Mood, columns by Voice, rows by Tense,
    # cells = 6-grid (3 persons × 2 numbers).
    moods_present = sorted(
        {k[0] for k in finite},
        key=lambda m: _VERB_MOOD_ORDER.index(m) if m in _VERB_MOOD_ORDER else 99,
    )
    for mood in moods_present:
        voices_present = sorted(
            {k[2] for k in finite if k[0] == mood},
            key=lambda v: _VERB_VOICE_ORDER.index(v) if v in _VERB_VOICE_ORDER else 99,
        )
        tenses_present = sorted(
            {k[1] for k in finite if k[0] == mood},
            key=_tense_sort_key,
        )
        rows = []
        for tense in tenses_present:
            cells_by_voice = {}
            for voice in voices_present:
                cells = finite.get((mood, tense, voice), {})
                grid = [
                    [cells.get((p, n), []) for p in _PERSONS]
                    for n in _NUMBERS
                ]
                cells_by_voice[voice] = grid
            # Drop the row if every cell across every voice is empty —
            # e.g. Latin synthetic Perfect Passive doesn't exist; the
            # library doesn't emit those forms, so the row is all dashes.
            any_filled = any(
                any(any(grid[i][j] for j in range(len(_PERSONS))) for i in range(len(_NUMBERS)))
                for grid in cells_by_voice.values()
            )
            if any_filled:
                rows.append({"tense": tense, "voices": cells_by_voice})
        blocks.append({
            "kind": "finite",
            "title": _MOOD_LABEL.get(mood, mood),
            "voices": voices_present,
            "rows": rows,
        })

    # Non-finite blocks
    if infinitives:
        rows = []
        seen_keys = sorted(infinitives.keys(), key=lambda k: (_tense_sort_key(k[0]), k[1]))
        for tense, voice in seen_keys:
            rows.append({
                "label": f"{_TENSE_LABEL.get(tense, tense)} {_VOICE_LABEL.get(voice, voice)}",
                "forms": infinitives[(tense, voice)],
            })
        blocks.append({"kind": "list", "title": "Infinitives", "rows": rows})

    if participles:
        prows = []
        for tense, voice in sorted(participles.keys(), key=lambda k: (_tense_sort_key(k[0]), k[1])):
            heading = f"{_TENSE_LABEL.get(tense, tense)} {_VOICE_LABEL.get(voice, voice)}"
            decl = _decline(participles[(tense, voice)])
            prows.append({"label": heading, "decl": decl})
        blocks.append({"kind": "participles", "title": "Participles", "rows": prows})

    def _case_idx(item: dict) -> int:
        c = item.get("case", "")
        return _NOUN_CASE_ORDER.index(c) if c in _NOUN_CASE_ORDER else 99

    if gerunds:
        rows = [
            {"label": _CASE_LABEL.get(g["case"], g["case"]) or "—", "forms": [g["form"]]}
            for g in sorted(gerunds, key=_case_idx)
        ]
        blocks.append({"kind": "list", "title": "Gerund", "rows": rows})

    if supines:
        rows = [
            {"label": _CASE_LABEL.get(s["case"], s["case"]) or "—", "forms": [s["form"]]}
            for s in sorted(supines, key=_case_idx)
        ]
        blocks.append({"kind": "list", "title": "Supine", "rows": rows})

    return {
        "kind": "verb",
        "blocks": blocks,
        "alternates": alternates,
        "total": len(forms),
    }


# ---------------------------------------------------------------------------
# Adjectives
# ---------------------------------------------------------------------------


def _layout_adj(forms: list[dict]) -> dict[str, Any]:
    by_degree: dict[str, list[dict]] = {}
    alternates: list[dict] = []
    for f in forms:
        feats = f.get("feats") or {}
        degree = feats.get("Degree", "Pos")
        if not feats.get("Case"):
            alternates.append(_alt(f))
            continue
        by_degree.setdefault(degree, []).append({
            "form": f["form"],
            "case": feats.get("Case", ""),
            "number": feats.get("Number", ""),
            "gender": feats.get("Gender", ""),
        })

    blocks = []
    for degree in sorted(
        by_degree.keys(),
        key=lambda d: _DEGREE_ORDER.index(d) if d in _DEGREE_ORDER else 99,
    ):
        decl = _decline(by_degree[degree])
        blocks.append({
            "kind": "decl",
            "title": _DEGREE_LABEL.get(degree, degree),
            "decl": decl,
        })

    return {
        "kind": "adj",
        "blocks": blocks,
        "alternates": alternates,
        "total": len(forms),
    }


# ---------------------------------------------------------------------------
# Nouns
# ---------------------------------------------------------------------------


def _layout_noun(forms: list[dict]) -> dict[str, Any]:
    """Nouns get a flat Case × Number grid — gender lives in the lexicon
    entry header, not as a column. The library sometimes emits multiple
    genders per noun (e.g. vir tagged Masc/Neut/Common across forms);
    splitting on that produces mostly-empty columns that obscure the
    actual paradigm."""
    items = []
    alternates = []
    for f in forms:
        feats = f.get("feats") or {}
        if not feats.get("Case"):
            alternates.append(_alt(f))
            continue
        items.append({
            "form": f["form"],
            "case": feats.get("Case", ""),
            "number": feats.get("Number", ""),
            "gender": "",  # collapse — nouns don't decline by gender
        })
    decl = _decline(items)
    blocks = [{"kind": "decl", "title": "Forms", "decl": decl}]
    return {
        "kind": "noun",
        "blocks": blocks,
        "alternates": alternates,
        "total": len(forms),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decline(items: list[dict]) -> dict[str, Any]:
    """Build a Case × Number grid, optionally split by Gender.

    Returns:
        {
            "genders": [...] | None,  # None for noun-style single-gender
            "cases": [...],
            "numbers": [...],
            "cells": {(case, number, gender): [forms]},
        }
    """
    genders = sorted(
        {i["gender"] for i in items if i["gender"]},
        key=lambda g: _GENDER_ORDER.index(g) if g in _GENDER_ORDER else 99,
    )
    cases = sorted(
        {i["case"] for i in items if i["case"]},
        key=lambda c: _NOUN_CASE_ORDER.index(c) if c in _NOUN_CASE_ORDER else 99,
    )
    numbers = sorted(
        {i["number"] for i in items if i["number"]},
        key=lambda n: _NUMBERS.index(n) if n in _NUMBERS else 99,
    )
    cells: dict[tuple[str, str, str], list[str]] = {}
    for it in items:
        cells.setdefault(
            (it["case"], it["number"], it["gender"]), []
        ).append(it["form"])
    # Latin adjectives have syncretic Dat/Abl Plur forms (e.g. `bonis`
    # serves all three genders); the library tags those forms gender-less.
    # Splat any gender-less cell across each present-gender column so
    # they render in the per-gender table instead of being dropped.
    if len(genders) > 1:
        for (c, n, g), cell in list(cells.items()):
            if g == "":
                for g2 in genders:
                    cells.setdefault((c, n, g2), []).extend(cell)
    return {
        "genders": genders if len(genders) > 1 else None,
        "single_gender": genders[0] if len(genders) == 1 else "",
        "cases": cases,
        "numbers": numbers,
        "cells": cells,
    }


def _layout_other(forms: list[dict]) -> dict[str, Any]:
    """Fallback: list every form. Used for closed-class / unknown POS.

    Indeclinables (e.g. `cum`) commonly arrive with empty-string forms and
    many byte-identical entries; drop empties and collapse exact (form,
    upos, feats) duplicates. Each surviving row carries a label like
    ``ADP, Case=Abl`` so users can tell distinct readings of the same
    surface (preposition vs adverb) apart in the rendered list.

    Also drops the synthetic ADV ``Degree=Cmp``/``Degree=Sup`` rows that
    the library emits for every adverb regardless of whether the word
    actually compares: if their surface equals a bare/``Degree=Pos`` ADV
    row, they're not real comparatives (e.g. *cum* never becomes *cumius*)
    and clutter the table. Genuinely comparable adverbs like *celeriter
    / celerius / celerrime* keep all three rows because their surfaces
    differ.
    """
    # Build the set of (upos, form) pairs that have a bare or Pos degree
    # reading — any Cmp/Sup form whose surface is already in this set is
    # synthetic and gets dropped.
    bare_or_pos: set[tuple[str, str]] = set()
    for f in forms:
        if not f.get("form"):
            continue
        deg = (f.get("feats") or {}).get("Degree")
        if deg in (None, "Pos"):
            bare_or_pos.add((f.get("upos") or "", f["form"]))

    rows: list[dict] = []
    seen: set[tuple] = set()
    for f in forms:
        form_val = f.get("form") or ""
        if not form_val:
            continue
        upos = f.get("upos") or ""
        feats = f.get("feats") or {}
        deg = feats.get("Degree")
        if deg in ("Cmp", "Sup") and (upos, form_val) in bare_or_pos:
            continue
        key = (form_val, upos, tuple(sorted(feats.items())))
        if key in seen:
            continue
        seen.add(key)
        feat_str = ", ".join(f"{k}={v}" for k, v in feats.items())
        label = ", ".join(part for part in (upos, feat_str) if part)
        rows.append({"label": label, "forms": [form_val]})
    surfaces = {r["forms"][0] for r in rows}
    title = "Indeclinable" if len(surfaces) == 1 else "Forms"
    return {
        "kind": "other",
        "blocks": [{"kind": "list", "title": title, "rows": rows}],
        "alternates": [],
        "total": len(rows),
    }


def _alt(f: dict) -> dict:
    feats = f.get("feats") or {}
    return {"form": f["form"], "feats": ", ".join(f"{k}={v}" for k, v in feats.items())}


def _tense_sort_key(tense: str) -> int:
    if tense in _VERB_TENSE_ORDER:
        return _VERB_TENSE_ORDER.index(tense)
    return 99


# Forms of `sum` keyed by (mood, tense), in order
# [1sg, 2sg, 3sg, 1pl, 2pl, 3pl]. Used to synthesize periphrastic
# perfect-system passive forms (e.g. amatus sum, amatus eram). The
# library tags Perfect as ``Past`` (with ``Pst`` declared as an alias
# but not actually emitted), so we only synthesize for ``Past``.
_SUM_AUX_FORMS: dict[tuple[str, str], list[str]] = {
    ("Ind", "Past"): ["sum", "es", "est", "sumus", "estis", "sunt"],
    ("Ind", "Pqp"): ["eram", "eras", "erat", "eramus", "eratis", "erant"],
    ("Ind", "FutP"): ["ero", "eris", "erit", "erimus", "eritis", "erunt"],
    ("Sub", "Past"): ["sim", "sis", "sit", "simus", "sitis", "sint"],
    ("Sub", "Pqp"): ["essem", "esses", "esset", "essemus", "essetis", "essent"],
}


def _synth_periphrastic_passive(finite: dict, participles: dict) -> None:
    """Fill in periphrastic Perfect/Pluperfect/Future-Perfect Passive
    cells using the verb's PPP + forms of ``sum``. Mutates ``finite``
    in place. Uses the masculine Nom Sing/Plur PPP forms (textbook
    convention); skips any (mood, tense) the library already populated,
    and skips when no Active forms exist for the tense (avoids creating
    a phantom row whose Active column is all dashes).
    """
    pp_sing = pp_plur = ""
    for p in participles.get(("Past", "Pass"), []):
        if p["case"] != "Nom" or p["gender"] != "Masc":
            continue
        if p["number"] == "Sing":
            pp_sing = p["form"]
        elif p["number"] == "Plur":
            pp_plur = p["form"]
    if not pp_sing or not pp_plur:
        return
    for (mood, tense), aux in _SUM_AUX_FORMS.items():
        if finite.get((mood, tense, "Pass")):
            continue
        if not finite.get((mood, tense, "Act")):
            continue
        finite[(mood, tense, "Pass")] = {
            ("1", "Sing"): [f"{pp_sing} {aux[0]}"],
            ("2", "Sing"): [f"{pp_sing} {aux[1]}"],
            ("3", "Sing"): [f"{pp_sing} {aux[2]}"],
            ("1", "Plur"): [f"{pp_plur} {aux[3]}"],
            ("2", "Plur"): [f"{pp_plur} {aux[4]}"],
            ("3", "Plur"): [f"{pp_plur} {aux[5]}"],
        }


def _synth_gerund(gerunds: list, participles: dict) -> None:
    """Synthesize the gerund block from the gerundive (Future Passive
    Participle). For 1st conj, FPP Neut Sing forms ``amandi / amando /
    amandum / amando`` are exactly the gerund's Gen / Dat / Acc / Abl.
    Skip if the library already emitted gerund forms or if no FPP exists.
    """
    if gerunds:
        return
    fpp_neut_sing = [
        p for p in participles.get(("Fut", "Pass"), [])
        if p["gender"] == "Neut" and p["number"] == "Sing"
    ]
    for case in ("Gen", "Dat", "Acc", "Abl"):
        match = next((p for p in fpp_neut_sing if p["case"] == case), None)
        if match:
            gerunds.append({"form": match["form"], "case": case, "number": "Sing"})


def _synth_multiword_infinitives(
    infinitives: dict, participles: dict, supines: list, has_real_ppp: bool
) -> None:
    """Build multi-word infinitives from existing participle / supine
    forms. Convention from Wiktionary's amo chart:

    - Fut Act:        FAP Acc Sing Neut + ``esse``     → amaturum esse
    - Fut Pass:       supine Acc        + ``iri``      → amatum iri
    - Perf Pass:      PPP Acc Sing Neut + ``esse``     → amatum esse
    - Fut Perf:       PPP Acc Sing Neut + ``fore``     → amatum fore
    - Perf Potential: FAP Acc Sing Neut + ``fuisse``   → amaturum fuisse

    Skip Pass / Fut Perf forms when the verb lacks a real PPP (e.g.
    sum: futurum esse is real, futum iri / futum esse are not). Skip
    any (tense, voice) the library already emitted.
    """
    fap_acc_neut = _find_part(participles, ("Fut", "Act"), "Acc")
    ppp_acc_neut = _find_part(participles, ("Past", "Pass"), "Acc") if has_real_ppp else None
    sup_acc = next((s["form"] for s in supines if s["case"] == "Acc"), None)

    if fap_acc_neut and ("Fut", "Act") not in infinitives:
        infinitives[("Fut", "Act")] = [f"{fap_acc_neut} esse"]
    if has_real_ppp and sup_acc and ("Fut", "Pass") not in infinitives:
        infinitives[("Fut", "Pass")] = [f"{sup_acc} iri"]
    if ppp_acc_neut and ("Past", "Pass") not in infinitives:
        infinitives[("Past", "Pass")] = [f"{ppp_acc_neut} esse"]
    if ppp_acc_neut and ("FutP", "Pass") not in infinitives:
        infinitives[("FutP", "Pass")] = [f"{ppp_acc_neut} fore"]
    if fap_acc_neut and ("PfPot", "Act") not in infinitives:
        infinitives[("PfPot", "Act")] = [f"{fap_acc_neut} fuisse"]


def _find_part(participles: dict, key: tuple[str, str], case: str) -> str | None:
    for p in participles.get(key, []):
        if p["gender"] == "Neut" and p["number"] == "Sing" and p["case"] == case:
            return p["form"]
    return None


def _route_finite(
    f: dict,
    form: str,
    feats: dict,
    pres_stem: str,
    perf_stem: str,
    conj: int | None,
    finite: dict,
    alternates: list,
) -> None:
    mood = feats.get("Mood")
    tense = feats.get("Tense")
    voice = feats.get("Voice", "Act")
    person = feats.get("Person")
    number = feats.get("Number")
    # Library tags both `amabo` (Fut) and `amavero` (FutP) as Tense=Fut;
    # reclassify when form looks like a perfect-stem FutP. The perfect-stem
    # guard prevents mis-grabbing `sum`'s canonical Future 1sg `ero`.
    if (
        tense == "Fut"
        and perf_stem
        and form.startswith(perf_stem)
        and form.endswith(_FUT_PERF_ENDINGS)
    ):
        tense = "FutP"
    if not (mood and tense and person and number):
        alternates.append(_alt(f))
        return
    if _is_finite_alternate(
        form, mood, tense, conj, pres_stem, perf_stem,
        person=person, number=number, voice=voice,
    ):
        alternates.append(_alt(f))
        return
    finite.setdefault((mood, tense, voice), {}).setdefault(
        (person, number), []
    ).append(form)


def _verb_stems(entry: dict | None) -> tuple[str, str, int | None, bool, str]:
    """Extract (present_stem, perfect_stem, conj, has_real_ppp, supine_stem).

    Whitaker's stem layout varies. 1st-conj entries are laid out as
    [pres, pres, perf] (e.g. amo → ['am','am','amass']). Irregulars use
    [pres, perf, sup] (e.g. sum → ['s','fu','fut']). 4-stem entries are
    [pres, pres2, perf, sup] (e.g. audio → ['audi','aud','audiv','audit']).
    Distinguish the 3-stem cases by checking whether stems[1] duplicates
    the present (1st-conj-style) or whether stems[2] looks like a supine
    derived from stems[1] (irregular-style).

    1st-conj perfect is stored syncopated as ``-ass`` (from amasse etc.);
    rewrite back to canonical ``-av`` so prefix matches catch ``amavero``.

    ``has_real_ppp`` flags whether the verb has a true perfect passive
    participle (e.g. ``amatus``). False for irregular verbs like sum
    where the library mechanically declines the supine stem as if it
    were a PPP, producing non-existent ``futus, futa, futum`` etc.

    ``supine_stem`` is used to filter wrong-conj participles. For 4-stem
    entries it's stems[3] (e.g. audit, dict). For 1st-conj 3-stem entries
    it's synthesized as ``pres + 'at'`` (amat, portat). Empty when not
    derivable.

    Returns empty strings + conj=None + ppp=False + sup="" for missing.
    """
    if not entry:
        return "", "", None, False, ""
    hw = entry.get("headword") or ""
    stems = entry.get("principal_parts") or []
    if not hw or not stems:
        return "", "", None, False, ""
    conj = _detect_conj(hw, stems)
    pres = stems[0]
    perf, has_ppp = _select_perf_stem(pres, stems)
    if conj == 1 and perf.endswith("ass"):
        perf = perf[:-3] + "av"
    sup = _select_supine_stem(pres, conj, stems, has_ppp)
    return pres, perf, conj, has_ppp, sup


def _select_supine_stem(pres: str, conj: int | None, stems: list[str], has_ppp: bool) -> str:
    if len(stems) >= 4:
        return stems[3]
    if conj == 1 and pres and has_ppp:
        return pres + "at"  # amat, portat — synthesized
    return ""


def _select_perf_stem(pres: str, stems: list[str]) -> tuple[str, bool]:
    """Return (perfect_stem, has_real_ppp). See _verb_stems."""
    if len(stems) >= 4:
        return stems[2], True
    if len(stems) == 3:
        s1, s2 = stems[1], stems[2]
        if s1 == pres:
            return s2, True  # 1st-conj-style: stems[2] is perfect, supine implied
        if s2.startswith(s1) and len(s2) > len(s1):
            return s1, False  # irregular: stems[2] is supine, no real PPP
        return s2, True
    if len(stems) == 2:
        return stems[1], False
    return "", False


def _detect_conj(hw: str, stems: list[str]) -> int | None:
    """Mirror of principal_parts._detect_conj — kept local so layout
    can stay independent. Returns 1, 2, 3, 4, or None.
    """
    if hw.endswith("eo"):
        return 2
    if hw.endswith("io"):
        return 4
    if hw.endswith("o"):
        pres = stems[0] if stems else ""
        perf = stems[2] if len(stems) >= 3 else ""
        if perf and perf != pres and perf.startswith(pres):
            suffix = perf[len(pres):]
            if suffix in {"av", "ass", "at"}:
                return 1
        return 3
    return None


# Canonical suffixes after the present stem for present-system finite
# forms, keyed by (conj, mood, tense, voice). Each value maps
# (person, number) -> set of acceptable suffixes (some cells have
# multiple, e.g. amaris/amare for Pres Ind Pass 2sg). Filters out
# library artefacts like rego's bare-stem ``reg``, audio's wrong-stem
# ``audbam``, and dico's 1st-conj-style ``dicas`` (mistagged).
def _build_pres_sys_endings() -> dict[tuple[int, str, str, str], dict[tuple[str, str], set[str]]]:
    out: dict[tuple[int, str, str, str], dict[tuple[str, str], set[str]]] = {}

    def add(conj: int, mood: str, tense: str, voice: str, sufs: list, alts: dict | None = None):
        cell = {
            ("1", "Sing"): {sufs[0]}, ("2", "Sing"): {sufs[1]}, ("3", "Sing"): {sufs[2]},
            ("1", "Plur"): {sufs[3]}, ("2", "Plur"): {sufs[4]}, ("3", "Plur"): {sufs[5]},
        }
        if alts:
            for k, v in alts.items():
                cell[k] = cell[k] | {v}
        out[(conj, mood, tense, voice)] = cell

    # ---- Conjugation 1 (am-) ----
    add(1, "Ind", "Pres", "Act", ["o", "as", "at", "amus", "atis", "ant"])
    add(1, "Ind", "Pres", "Pass", ["or", "aris", "atur", "amur", "amini", "antur"], {("2", "Sing"): "are"})
    add(1, "Ind", "Imp", "Act", ["abam", "abas", "abat", "abamus", "abatis", "abant"])
    add(1, "Ind", "Imp", "Pass", ["abar", "abaris", "abatur", "abamur", "abamini", "abantur"], {("2", "Sing"): "abare"})
    add(1, "Ind", "Fut", "Act", ["abo", "abis", "abit", "abimus", "abitis", "abunt"])
    add(1, "Ind", "Fut", "Pass", ["abor", "aberis", "abitur", "abimur", "abimini", "abuntur"], {("2", "Sing"): "abere"})
    add(1, "Sub", "Pres", "Act", ["em", "es", "et", "emus", "etis", "ent"])
    add(1, "Sub", "Pres", "Pass", ["er", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(1, "Sub", "Imp", "Act", ["arem", "ares", "aret", "aremus", "aretis", "arent"])
    add(1, "Sub", "Imp", "Pass", ["arer", "areris", "aretur", "aremur", "aremini", "arentur"], {("2", "Sing"): "arere"})
    out[(1, "Imp", "Pres", "Act")] = {("2", "Sing"): {"a"}, ("2", "Plur"): {"ate"}}
    out[(1, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"are"}, ("2", "Plur"): {"amini"}}
    out[(1, "Imp", "Fut", "Act")] = {("2", "Sing"): {"ato"}, ("3", "Sing"): {"ato"},
                                       ("2", "Plur"): {"atote"}, ("3", "Plur"): {"anto"}}
    out[(1, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"ator"}, ("3", "Sing"): {"ator"}, ("3", "Plur"): {"antor"}}

    # ---- Conjugation 2 (mon-) ----
    add(2, "Ind", "Pres", "Act", ["eo", "es", "et", "emus", "etis", "ent"])
    add(2, "Ind", "Pres", "Pass", ["eor", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(2, "Ind", "Imp", "Act", ["ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"])
    add(2, "Ind", "Imp", "Pass", ["ebar", "ebaris", "ebatur", "ebamur", "ebamini", "ebantur"], {("2", "Sing"): "ebare"})
    add(2, "Ind", "Fut", "Act", ["ebo", "ebis", "ebit", "ebimus", "ebitis", "ebunt"])
    add(2, "Ind", "Fut", "Pass", ["ebor", "eberis", "ebitur", "ebimur", "ebimini", "ebuntur"], {("2", "Sing"): "ebere"})
    add(2, "Sub", "Pres", "Act", ["eam", "eas", "eat", "eamus", "eatis", "eant"])
    add(2, "Sub", "Pres", "Pass", ["ear", "earis", "eatur", "eamur", "eamini", "eantur"], {("2", "Sing"): "eare"})
    add(2, "Sub", "Imp", "Act", ["erem", "eres", "eret", "eremus", "eretis", "erent"])
    add(2, "Sub", "Imp", "Pass", ["erer", "ereris", "eretur", "eremur", "eremini", "erentur"], {("2", "Sing"): "erere"})
    out[(2, "Imp", "Pres", "Act")] = {("2", "Sing"): {"e"}, ("2", "Plur"): {"ete"}}
    out[(2, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"ere"}, ("2", "Plur"): {"emini"}}
    out[(2, "Imp", "Fut", "Act")] = {("2", "Sing"): {"eto"}, ("3", "Sing"): {"eto"},
                                       ("2", "Plur"): {"etote"}, ("3", "Plur"): {"ento"}}
    out[(2, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"etor"}, ("3", "Sing"): {"etor"}, ("3", "Plur"): {"entor"}}

    # ---- Conjugation 3 (reg-, dic-) ----
    add(3, "Ind", "Pres", "Act", ["o", "is", "it", "imus", "itis", "unt"])
    add(3, "Ind", "Pres", "Pass", ["or", "eris", "itur", "imur", "imini", "untur"], {("2", "Sing"): "ere"})
    add(3, "Ind", "Imp", "Act", ["ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"])
    add(3, "Ind", "Imp", "Pass", ["ebar", "ebaris", "ebatur", "ebamur", "ebamini", "ebantur"], {("2", "Sing"): "ebare"})
    add(3, "Ind", "Fut", "Act", ["am", "es", "et", "emus", "etis", "ent"])
    add(3, "Ind", "Fut", "Pass", ["ar", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(3, "Sub", "Pres", "Act", ["am", "as", "at", "amus", "atis", "ant"])
    add(3, "Sub", "Pres", "Pass", ["ar", "aris", "atur", "amur", "amini", "antur"], {("2", "Sing"): "are"})
    add(3, "Sub", "Imp", "Act", ["erem", "eres", "eret", "eremus", "eretis", "erent"])
    add(3, "Sub", "Imp", "Pass", ["erer", "ereris", "eretur", "eremur", "eremini", "erentur"], {("2", "Sing"): "erere"})
    out[(3, "Imp", "Pres", "Act")] = {("2", "Sing"): {"e"}, ("2", "Plur"): {"ite"}}
    out[(3, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"ere"}, ("2", "Plur"): {"imini"}}
    out[(3, "Imp", "Fut", "Act")] = {("2", "Sing"): {"ito"}, ("3", "Sing"): {"ito"},
                                       ("2", "Plur"): {"itote"}, ("3", "Plur"): {"unto"}}
    out[(3, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"itor"}, ("3", "Sing"): {"itor"}, ("3", "Plur"): {"untor"}}

    # ---- Conjugation 4 (audi-) — pres stem already includes theme vowel `i` ----
    add(4, "Ind", "Pres", "Act", ["o", "s", "t", "mus", "tis", "unt"])
    add(4, "Ind", "Pres", "Pass", ["or", "ris", "tur", "mur", "mini", "untur"], {("2", "Sing"): "re"})
    add(4, "Ind", "Imp", "Act", ["ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"])
    add(4, "Ind", "Imp", "Pass", ["ebar", "ebaris", "ebatur", "ebamur", "ebamini", "ebantur"], {("2", "Sing"): "ebare"})
    add(4, "Ind", "Fut", "Act", ["am", "es", "et", "emus", "etis", "ent"])
    add(4, "Ind", "Fut", "Pass", ["ar", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(4, "Sub", "Pres", "Act", ["am", "as", "at", "amus", "atis", "ant"])
    add(4, "Sub", "Pres", "Pass", ["ar", "aris", "atur", "amur", "amini", "antur"], {("2", "Sing"): "are"})
    add(4, "Sub", "Imp", "Act", ["rem", "res", "ret", "remus", "retis", "rent"])
    add(4, "Sub", "Imp", "Pass", ["rer", "reris", "retur", "remur", "remini", "rentur"], {("2", "Sing"): "rere"})
    out[(4, "Imp", "Pres", "Act")] = {("2", "Sing"): {""}, ("2", "Plur"): {"te"}}
    out[(4, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"re"}, ("2", "Plur"): {"mini"}}
    out[(4, "Imp", "Fut", "Act")] = {("2", "Sing"): {"to"}, ("3", "Sing"): {"to"},
                                       ("2", "Plur"): {"tote"}, ("3", "Plur"): {"unto"}}
    out[(4, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"tor"}, ("3", "Sing"): {"tor"}, ("3", "Plur"): {"untor"}}
    return out


_PRES_SYS_ENDINGS = _build_pres_sys_endings()
_FUT_IND_PREFIX = {1: "ab", 2: "eb"}


def _is_finite_alternate(
    form: str,
    mood: str,
    tense: str,
    conj: int | None,
    pres_stem: str,
    perf_stem: str,
    person: str = "",
    number: str = "",
    voice: str = "",
) -> bool:
    """Return True if a finite form should be routed to alternates rather
    than placed in its canonical paradigm cell. Catches Plautine sigmatic
    forms (``amasso, amassi, amasseram, amassero``) and the library's
    wrong-stem / wrong-conj artefacts (``reg``, ``audbam``, ``dicas``).

    Conservative: when stems are unknown (irregular verb without detected
    conj) we keep the form in-cell rather than risk false alternates.
    """
    if not perf_stem and not pres_stem:
        return False
    if tense in _PERF_SYS_TENSES:
        return bool(perf_stem) and not form.startswith(perf_stem)
    if conj and pres_stem and tense in {"Pres", "Imp", "Fut"}:
        endings = _PRES_SYS_ENDINGS.get((conj, mood, tense, voice), {})
        valid = endings.get((person, number)) if (person and number) else None
        if valid is not None:
            if not form.startswith(pres_stem):
                return True
            suffix = form[len(pres_stem):]
            return suffix not in valid
    if tense == "Fut" and mood == "Ind" and pres_stem and conj in _FUT_IND_PREFIX:
        return not form.startswith(pres_stem + _FUT_IND_PREFIX[conj])
    return False


def _is_part_alternate(
    form: str, tense: str, voice: str, conj: int | None,
    pres_stem: str, sup_stem: str,
) -> bool:
    """Route participles built from the wrong stem to alternates. The
    library lumps homonyms (dicere + dicare) into one paradigm, emitting
    both ``dicens`` / ``dicans`` etc.; this filter keeps only the forms
    consistent with the entry's principal parts.

    Conservative: when the relevant stem is missing we keep the form.
    """
    if not (pres_stem or sup_stem):
        return False
    if voice == "Pass" and tense == "Past":
        return bool(sup_stem) and not form.startswith(sup_stem)
    if voice == "Act" and tense == "Fut":
        return bool(sup_stem) and not form.startswith(sup_stem)
    if not (conj and pres_stem and form.startswith(pres_stem)):
        # Conservative: if we can't apply the conj-specific rule, keep it.
        return False
    after = form[len(pres_stem):]
    if voice == "Act" and tense == "Pres":
        if conj == 1:
            return not after.startswith(("an", "ant"))
        return not after.startswith(("en", "ient"))
    if voice == "Pass" and tense == "Fut":
        if conj == 1:
            return not after.startswith("and")
        if conj == 4:
            return not after.startswith(("end", "iend"))
        return not after.startswith(("end", "und"))
    return False


def _is_inf_alternate(form: str, tense: str, voice: str, perf_stem: str) -> bool:
    """Route non-canonical infinitives to alternates.

    Canonical Latin infinitive endings:
      - Pres Act: ``-re`` (amare, monere, regere, audire)
      - Pres Pass: ``-ri`` or bare ``-i`` (amari, moneri, regi, audiri)
      - Perf Act: ``-isse`` and starting with the perfect stem (amavisse)

    Catches archaic/poetic forms like ``amarier`` (Plautine Pres Pass)
    and library artefacts like ``ame`` mistagged as a Pres Act inf.
    """
    if tense in _PERF_SYS_TENSES:
        if perf_stem and not form.startswith(perf_stem):
            return True
        if voice == "Act" and not form.endswith("isse"):
            return True
        return False
    if tense == "Pres":
        if voice == "Act" and not form.endswith("re"):
            return True
        if voice == "Pass" and not (form.endswith("ri") or form.endswith("i")):
            return True
    return False


_MOOD_LABEL = {"Ind": "Indicative", "Sub": "Subjunctive", "Imp": "Imperative"}
_TENSE_LABEL = {
    "Pres": "Present",
    "Imp": "Imperfect",
    "Past": "Perfect",
    "Pst": "Perfect",
    "Fut": "Future",
    "Pqp": "Pluperfect",
    "FutP": "Future Perfect",
    "PfPot": "Perfect Potential",
}
_VOICE_LABEL = {"Act": "Active", "Pass": "Passive", "Mid": "Middle"}
_CASE_LABEL = {
    "Nom": "Nominative",
    "Gen": "Genitive",
    "Dat": "Dative",
    "Acc": "Accusative",
    "Abl": "Ablative",
    "Voc": "Vocative",
    "Loc": "Locative",
}
_DEGREE_LABEL = {"Pos": "Positive", "Cmp": "Comparative", "Sup": "Superlative"}
