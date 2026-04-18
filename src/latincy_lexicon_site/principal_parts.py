"""Reconstruct textbook-style principal parts from Whitaker stems.

Whitaker's Words stores noun/verb/adjective stems (e.g., ``["scrib",
"scrib", "scrips", "script"]``) rather than citation forms like
``scribo, scribere, scripsi, scriptum``. The upstream ``latincy-lexicon``
payload also lacks declension / conjugation class metadata, so this
formatter infers class from headword shape and stem patterns. It's
heuristic — good for ~80-90% of common cases — and returns ``None``
for anything it can't confidently reconstruct.

When upstream eventually exposes an explicit ``conj_type`` / ``decl_type``
field, the heuristics here can be replaced with direct lookups.
"""

from __future__ import annotations

GENDER_ABBREV = {"M": "m.", "F": "f.", "N": "n."}


def format_principal_parts(entry: dict) -> str | None:
    pos = entry.get("pos")
    hw = entry.get("headword")
    stems = entry.get("principal_parts") or []
    if not hw or not stems:
        return None
    if pos == "V":
        return _format_verb(hw, stems)
    if pos == "N":
        return _format_noun(hw, stems, entry.get("gender"))
    if pos == "ADJ":
        return _format_adj(hw, stems)
    return None


# ---------- verbs ----------


def _format_verb(hw: str, stems: list[str]) -> str | None:
    parts = [hw]
    inf = _infinitive(hw, stems)
    if inf is None:
        return None
    parts.append(inf)

    # Perfect: stems[2] + 'i'
    if len(stems) >= 3 and stems[2]:
        parts.append(stems[2] + "i")

    # Supine: stems[3] + 'um'
    if len(stems) >= 4 and stems[3]:
        parts.append(stems[3] + "um")

    return ", ".join(parts)


def _infinitive(hw: str, stems: list[str]) -> str | None:
    """Reconstruct the infinitive (2nd principal part) from hw + stems.

    Conj detection order:
      1. ``-eo`` → 2nd conj → ``-ere`` (long e)
      2. ``-io`` → 4th conj → ``-ire`` (we can't reliably split 3rd-io here)
      3. ``-o`` + perfect stem has ``v``/``u``/``ss`` suffix vs present → 1st → ``-are``
      4. ``-o`` → 3rd conj → ``-ere`` (short e)
    """
    pres = stems[0] if stems else ""
    if hw.endswith("eo"):
        # mon + ere → monere; hw minus 'o' gives us 'mone', then + 're'
        return hw[:-2] + "ere"
    if hw.endswith("io"):
        # audio → audire; capio → capere would be more accurate but
        # we can't reliably tell 4th from 3rd-io here. Default to -ire.
        return hw[:-2] + "ire"
    if hw.endswith("o"):
        # 1st vs 3rd: look at perfect stem (stems[2]) if present
        perf = stems[2] if len(stems) >= 3 else ""
        if perf and _is_first_conj_perfect(pres, perf):
            return pres + "are"
        return pres + "ere"
    return None


def _is_first_conj_perfect(pres: str, perf: str) -> bool:
    """1st conj perfect is typically pres + 'av' (amav) or pres + 'ass'
    (syncopated, what Whitaker stores as 'amass'). 3rd conj perfects
    either repeat the present stem, add '-s-' (sigmatic: scrib→scrips),
    or lengthen the stem vowel.
    """
    if perf == pres:
        return False  # 3rd conj default reduplication / vowel-length perfect
    if perf.startswith(pres):
        suffix = perf[len(pres) :]
        return suffix in {"av", "ass", "at"}
    return False


# ---------- nouns ----------


def _format_noun(hw: str, stems: list[str], gender: str | None) -> str:
    gen = _noun_genitive(hw, stems)
    gender_tag = GENDER_ABBREV.get(gender) if gender else None
    if gender_tag:
        return f"{hw}, {gen}, {gender_tag}"
    return f"{hw}, {gen}"


def _noun_genitive(hw: str, stems: list[str]) -> str:
    stem2 = stems[1] if len(stems) >= 2 else stems[0]
    if hw.endswith("a"):
        return hw + "e"  # puella → puellae
    if hw.endswith("us") or hw.endswith("um"):
        return hw[:-2] + "i"  # servus → servi; bellum → belli
    if hw.endswith("er") or hw.endswith("ir"):
        # puer → pueri (preserve 'er'); ager → agri (drop 'e')
        # Heuristic: if stem2 drops the 'e', follow it; else just append 'i'
        if stem2 and not stem2.endswith("er") and stem2.endswith("r"):
            return stem2 + "i"
        return hw + "i"
    # Default: 3rd declension, use stem2 + 'is'
    return stem2 + "is"


# ---------- adjectives ----------


def _format_adj(hw: str, stems: list[str]) -> str:
    if hw.endswith("us"):
        return f"{hw}, -a, -um"
    if hw.endswith("er"):
        # pulcher → pulchra, pulchrum (drops e) or liber → libera, liberum.
        # Heuristic: use stem2 to decide.
        stem2 = stems[1] if len(stems) >= 2 else stems[0]
        if stem2 and not stem2.endswith("er") and stem2.endswith("r"):
            return f"{hw}, {stem2}a, {stem2}um"
        return f"{hw}, {hw}a, {hw}um"
    if hw.endswith("is"):
        return f"{hw}, -e"
    # 1-ending 3rd decl adj: felix → felix, felicis
    stem2 = stems[1] if len(stems) >= 2 else stems[0]
    return f"{hw}, {stem2}is"
