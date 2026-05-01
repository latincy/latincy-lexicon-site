"""Convert UD-style morphological feats to a short textbook gloss.

The pipeline emits feats like ``{Mood: Ind, Number: Sing, Person: 3,
Tense: Pres, VerbForm: Fin, Voice: Act}`` — accurate but unreadable for
learners. ``morph_to_textbook`` renders the same content as
``"3rd person singular present indicative active"``, in the order
Latin teachers say it.
"""

from __future__ import annotations

_PERSON = {"1": "1st person", "2": "2nd person", "3": "3rd person"}
_NUMBER = {"Sing": "singular", "Plur": "plural", "Dual": "dual"}
_TENSE = {
    "Pres": "present",
    "Imp": "imperfect",
    "Fut": "future",
    "Past": "perfect",
    "Pst": "perfect",
    "Pqp": "pluperfect",
    "FutP": "future perfect",
}
_MOOD = {
    "Ind": "indicative",
    "Sub": "subjunctive",
    "Imp": "imperative",
}
_VOICE = {"Act": "active", "Pass": "passive", "Mid": "middle"}
_CASE = {
    "Nom": "nominative",
    "Gen": "genitive",
    "Dat": "dative",
    "Acc": "accusative",
    "Abl": "ablative",
    "Voc": "vocative",
    "Loc": "locative",
}
_GENDER = {"Masc": "masculine", "Fem": "feminine", "Neut": "neuter", "Com": "common"}
_DEGREE = {"Pos": "positive", "Cmp": "comparative", "Sup": "superlative"}


def _join(parts: list[str]) -> str:
    return " ".join(p for p in parts if p)


def morph_to_textbook(feats: dict[str, str] | None) -> str:
    """Return a short pedagogical gloss for a UD feats dict.

    Returns ``""`` when feats is empty or doesn't carry enough info to
    say anything useful (e.g. an indeclinable particle).
    """
    if not feats:
        return ""

    verbform = feats.get("VerbForm")
    if verbform == "Fin":
        return _join([
            _PERSON.get(feats.get("Person", ""), ""),
            _NUMBER.get(feats.get("Number", ""), ""),
            _TENSE.get(feats.get("Tense", ""), ""),
            _MOOD.get(feats.get("Mood", ""), ""),
            _VOICE.get(feats.get("Voice", ""), ""),
        ])
    if verbform == "Inf":
        return _join([
            _TENSE.get(feats.get("Tense", ""), ""),
            _VOICE.get(feats.get("Voice", ""), ""),
            "infinitive",
        ])
    if verbform == "Part":
        return _join([
            _TENSE.get(feats.get("Tense", ""), ""),
            _VOICE.get(feats.get("Voice", ""), ""),
            "participle",
            _CASE.get(feats.get("Case", ""), ""),
            _NUMBER.get(feats.get("Number", ""), ""),
            _GENDER.get(feats.get("Gender", ""), ""),
        ])
    if verbform == "Ger":
        return _join(["gerund", _CASE.get(feats.get("Case", ""), "")])
    if verbform == "Sup":
        return _join(["supine", _CASE.get(feats.get("Case", ""), "")])

    # Noun / adjective / pronoun: case number gender (degree)
    return _join([
        _CASE.get(feats.get("Case", ""), ""),
        _NUMBER.get(feats.get("Number", ""), ""),
        _GENDER.get(feats.get("Gender", ""), ""),
        _DEGREE.get(feats.get("Degree", ""), ""),
    ])
