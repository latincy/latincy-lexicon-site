"""Sense scoring abstraction.

Phase 1 ships `FrequencySenseScorer` — picks the highest-freq entry whose
`ud_pos` matches the annotated token POS. Phase 2 will add a cross-lingual
SBERT scorer that combines freq prior with Latin-sentence ↔ English-gloss
similarity; the Protocol here is the seam for that swap.
"""

from __future__ import annotations

from typing import Protocol

# Mirror of latincy-lexicon's _FREQ_SCORE. Duplicated rather than imported
# because the library keeps it module-private; the codes are stable.
_FREQ_SCORE: dict[str, float] = {
    "A": 1.0,
    "B": 0.8,
    "C": 0.6,
    "D": 0.4,
    "E": 0.2,
    "F": 0.1,
    "X": 0.3,
}

_NO_MATCH = float("-inf")


class SenseScorer(Protocol):
    def score(
        self,
        *,
        entries: list[dict],
        token_pos: str | None,
        sentence_text: str | None = None,
        token_index: int | None = None,
    ) -> list[float]: ...


class FrequencySenseScorer:
    """Score = Whitaker freq prior, gated on POS match."""

    def score(
        self,
        *,
        entries: list[dict],
        token_pos: str | None,
        sentence_text: str | None = None,
        token_index: int | None = None,
    ) -> list[float]:
        if not token_pos:
            return [_NO_MATCH] * len(entries)
        return [
            _FREQ_SCORE.get(e.get("freq", "X"), 0.3)
            if token_pos in (e.get("ud_pos") or [])
            else _NO_MATCH
            for e in entries
        ]


default_scorer: SenseScorer = FrequencySenseScorer()
