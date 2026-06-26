"""Map Whitaker POS codes to human labels.

Whitaker's Words uses compact POS tags (e.g., ``TACKON`` for enclitics
like ``-que``, ``PACKON`` for part-of-compound morphemes). These are
fine as data but opaque in a user-facing UI. This module provides an
expansion map for display.
"""

from __future__ import annotations

POS_LABELS: dict[str, str] = {
    "N": "noun",
    "V": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PRON": "pronoun",
    "PREP": "preposition",
    "CONJ": "conjunction",
    "INTERJ": "interjection",
    "NUM": "numeral",
    "TACKON": "enclitic",
    "PACKON": "part of compound",
    "PREFIX": "prefix",
    "SUFFIX": "suffix",
    "X": "unknown",
}


UPOS_LABELS: dict[str, str] = {
    "NOUN": "noun",
    "VERB": "verb",
    "AUX": "verb",
    "ADJ": "adj.",
    "ADV": "adv.",
    "ADP": "prep.",
    "CCONJ": "conj.",
    "SCONJ": "conj.",
    "PRON": "pronoun",
    "PROPN": "proper noun",
    "NUM": "numeral",
    "INTJ": "interj.",
    "PART": "particle",
    "DET": "det.",
    "X": "unknown",
}


def pos_label(code: str | None) -> str:
    if not code:
        return ""
    return POS_LABELS.get(code, code)


def upos_label(code: str | None) -> str:
    if not code:
        return ""
    return UPOS_LABELS.get(code, code.lower())
