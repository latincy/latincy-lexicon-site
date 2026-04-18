"""Whitaker's Words single-letter code → human label mappings.

Whitaker's Words encodes five metadata dimensions on each dictionary entry
as single letters: age (era), frequency, area (subject domain), geography,
and source (the lexical reference Whitaker drew from). These letters show
up in the lexicon payload and need expanding for the UI.
"""

from __future__ import annotations

AGE_LABELS: dict[str, str] = {
    "A": "Archaic (before 200 BC)",
    "B": "Early (200-81 BC)",
    "C": "Classical (80 BC – 17 AD)",
    "D": "Late (17-196 AD)",
    "E": "Later (197-575 AD)",
    "F": "Medieval (576-1300)",
    "G": "Scholarly (1301-1900)",
    "H": "Modern (1900-)",
    "X": "all eras",
}

FREQ_LABELS: dict[str, str] = {
    "A": "very frequent",
    "B": "frequent",
    "C": "common",
    "D": "less common",
    "E": "uncommon",
    "F": "very rare",
    "I": "inscription",
    "M": "graffiti",
    "N": "Pliny",
    "X": "unknown frequency",
}

AREA_LABELS: dict[str, str] = {
    "A": "agriculture",
    "B": "biology",
    "D": "drama / music",
    "E": "ecclesiastic / biblical",
    "G": "grammar / rhetoric",
    "L": "legal / government",
    "P": "poetic",
    "S": "science / mathematics",
    "T": "technical",
    "W": "military",
    "Y": "mythology",
    "X": "all domains",
}

GEO_LABELS: dict[str, str] = {
    "A": "Africa",
    "B": "Britain",
    "C": "China",
    "D": "Scandinavia",
    "E": "Egypt",
    "F": "France / Gaul",
    "G": "Germany",
    "H": "Greece",
    "I": "Italy / Rome",
    "J": "India",
    "K": "Balkans",
    "N": "Netherlands",
    "P": "Persia",
    "Q": "Near East",
    "R": "Russia",
    "S": "Spain / Iberia",
    "U": "Eastern Europe",
    "X": "all regions",
}

SOURCE_LABELS: dict[str, str] = {
    "B": "Bee (Latin-English)",
    "C": "Cicero",
    "D": "Lewis & Short",
    "L": "Lewis elementary",
    "O": "Oxford Latin Dictionary",
    "S": "Souter",
    "X": "general source",
}


def _lookup(table: dict[str, str], code: str | None) -> str:
    if not code:
        return ""
    return table.get(code, code)


def ww_age(code: str | None) -> str:
    return _lookup(AGE_LABELS, code)


def ww_freq(code: str | None) -> str:
    return _lookup(FREQ_LABELS, code)


def ww_area(code: str | None) -> str:
    return _lookup(AREA_LABELS, code)


def ww_geo(code: str | None) -> str:
    return _lookup(GEO_LABELS, code)


def ww_source(code: str | None) -> str:
    return _lookup(SOURCE_LABELS, code)
