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

# Display order for tense rows within a (mood, voice) block. Anything
# not listed lands in `extra_tenses` per block, surfaced after the
# canonical rows.
_VERB_TENSE_ORDER = ["Pres", "Imp", "Past", "Fut", "Pqp", "Pst", "FutP"]
_VERB_MOOD_ORDER = ["Ind", "Sub", "Imp"]
_VERB_VOICE_ORDER = ["Act", "Pass"]
_PERSONS = ["1", "2", "3"]
_NUMBERS = ["Sing", "Plur"]

_NOUN_CASE_ORDER = ["Nom", "Gen", "Dat", "Acc", "Abl", "Voc", "Loc"]
_GENDER_ORDER = ["Masc", "Fem", "Neut", "Com"]
_DEGREE_ORDER = ["Pos", "Cmp", "Sup"]


def layout_paradigm(forms: list[dict], upos: str | None) -> dict[str, Any]:
    """Return a structured layout suitable for paradigm.html rendering.

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
        return _layout_verb(forms)
    if kind_upos == "ADJ":
        return _layout_adj(forms)
    if kind_upos in {"NOUN", "PROPN"}:
        return _layout_noun(forms)
    return _layout_other(forms)


# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------


def _layout_verb(forms: list[dict]) -> dict[str, Any]:
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
            mood = feats.get("Mood")
            tense = feats.get("Tense")
            voice = feats.get("Voice", "Act")
            person = feats.get("Person")
            number = feats.get("Number")
            if mood and tense and person and number:
                cell_key = (person, number)
                finite.setdefault((mood, tense, voice), {}).setdefault(
                    cell_key, []
                ).append(form)
            else:
                alternates.append(_alt(f))
        elif vf == "Inf":
            tense = feats.get("Tense", "Pres")
            voice = feats.get("Voice", "Act")
            infinitives.setdefault((tense, voice), []).append(form)
        elif vf == "Part":
            tense = feats.get("Tense", "Pres")
            voice = feats.get("Voice", "Act")
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
    return {
        "genders": genders if len(genders) > 1 else None,
        "single_gender": genders[0] if len(genders) == 1 else "",
        "cases": cases,
        "numbers": numbers,
        "cells": cells,
    }


def _layout_other(forms: list[dict]) -> dict[str, Any]:
    """Fallback: list every form. Used for closed-class / unknown POS."""
    return {
        "kind": "other",
        "blocks": [
            {
                "kind": "list",
                "title": "Forms",
                "rows": [{"label": "", "forms": [f["form"]]} for f in forms],
            }
        ],
        "alternates": [],
        "total": len(forms),
    }


def _alt(f: dict) -> dict:
    feats = f.get("feats") or {}
    return {"form": f["form"], "feats": ", ".join(f"{k}={v}" for k, v in feats.items())}


def _tense_sort_key(tense: str) -> int:
    if tense in _VERB_TENSE_ORDER:
        return _VERB_TENSE_ORDER.index(tense)
    return 99


_MOOD_LABEL = {"Ind": "Indicative", "Sub": "Subjunctive", "Imp": "Imperative"}
_TENSE_LABEL = {
    "Pres": "Present",
    "Imp": "Imperfect",
    "Past": "Perfect",
    "Pst": "Perfect",
    "Fut": "Future",
    "Pqp": "Pluperfect",
    "FutP": "Future Perfect",
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
