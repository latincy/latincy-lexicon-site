"""spaCy pipeline load + warmup + async analyzer wrappers."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import latincy_lexicon

# Importing registers the spaCy factories for whitakers_words + paradigm_generator.
import latincy_lexicon.spacy  # noqa: F401
import spacy
from latincy_lexicon.build import build as build_lexicon
from spacy.language import Language

from latincy_lexicon_site.morph_gloss import morph_to_textbook
from latincy_lexicon_site.sense_scoring import SenseScorer, default_scorer

# la_core_web_{sm,lg} 3.9.0 pipes we don't need for lookup. Keep both
# lemmatizers — they complement each other (lookup handles common cases fast,
# trainable covers edge forms) and are cheap relative to parser/ner.
_PRUNE = [
    "senter",
    "normer",
    "uv_normalizer",
    "parser",
    "harmonizer",
    "remorpher",
    "ner",
]


def _cache_key() -> str:
    """Cache key that invalidates when lexicon code changes.

    Version alone is insufficient for editable installs (version doesn't
    bump on every code change). Add build.py mtime so local edits trigger
    a rebuild; version alone drives invalidation for PyPI installs.
    """
    build_py = Path(build_lexicon.__code__.co_filename)
    mtime = int(build_py.stat().st_mtime) if build_py.exists() else 0
    return f"{latincy_lexicon.__version__}-{mtime}"


def _build_lexicon_artifacts() -> tuple[Path, Path]:
    """Run latincy-lexicon's build() once per (version, build.py mtime), cache under tmp."""
    out = Path(tempfile.gettempdir()) / "latincy-lexicon-site" / _cache_key()
    out.mkdir(parents=True, exist_ok=True)
    lexicon_path = out / "lexicon.json"
    analyzer_path = out / "analyzer.json"
    if not (lexicon_path.exists() and analyzer_path.exists()):
        build_lexicon(output_dir=out)
    return lexicon_path, analyzer_path


def load_pipeline(model_name: str = "la_core_web_lg") -> Language:
    """Load a LatinCy model with pruned pipes + lexicon components attached."""
    nlp = spacy.load(model_name, disable=_PRUNE)

    lexicon_path, analyzer_path = _build_lexicon_artifacts()
    nlp.add_pipe(
        "whitakers_words",
        config={
            "lexicon_path": str(lexicon_path),
            "analyzer_path": str(analyzer_path),
        },
        last=True,
    )
    nlp.add_pipe(
        "paradigm_generator",
        config={"analyzer_path": str(analyzer_path)},
        last=True,
    )
    return nlp


def warmup(nlp: Language) -> None:
    """Force lazy JIT paths before accepting traffic."""
    nlp("arma uirumque cano")


def _clean_entry(entry: dict) -> dict:
    """Normalize a raw whitakers_words entry for display.

    - Strip leading `|` from glosses (Whitaker encoding quirk where `|`
      separates alternative senses but leaks through as a literal prefix).
    """
    glosses = entry.get("glosses")
    if isinstance(glosses, list):
        cleaned = [
            g.lstrip("|").lstrip() if isinstance(g, str) else g for g in glosses
        ]
        return {**entry, "glosses": cleaned}
    return entry


def _is_morpheme_entry(entry: dict) -> bool:
    """True for Whitaker prefix / suffix entries — useful for morphology
    tools, noisy for a word-lookup UI."""
    return entry.get("pos") in {"PREFIX", "SUFFIX"}


def _filter_entries(entries: list[dict] | None) -> list[dict]:
    return [_clean_entry(e) for e in (entries or []) if not _is_morpheme_entry(e)]


def _annotate_senses(
    entries: list[dict],
    token_pos: str | None,
    *,
    sentence_text: str | None = None,
    token_index: int | None = None,
    scorer: SenseScorer = default_scorer,
) -> list[dict]:
    """Tag at most one entry with `top_sense=True` — the single best-scored
    candidate for the annotated token POS. Drives both the accent styling
    and the ✓ badge in the expanded view; everything else renders muted.

    Scoring is delegated so phase 2 can swap in a cross-lingual SBERT
    scorer without touching the pipeline.
    """
    if not entries:
        return entries
    scores = scorer.score(
        entries=entries,
        token_pos=token_pos,
        sentence_text=sentence_text,
        token_index=token_index,
    )
    best_idx: int | None = None
    best_score = float("-inf")
    for i, s in enumerate(scores):
        if s > best_score:
            best_score = s
            best_idx = i
    if best_score == float("-inf"):
        best_idx = None
    return [
        {**e, "top_sense": (i == best_idx)} for i, e in enumerate(entries)
    ]


def _token_to_dict(token) -> dict:
    entries = _annotate_senses(
        _filter_entries(token._.lexicon),
        token.pos_,
        sentence_text=token.doc.text,
        token_index=token.i,
    )
    return {
        "text": token.text,
        "lemma": token.lemma_,
        "pos": token.pos_,
        "tag": token.tag_,
        "morph": str(token.morph),
        "entries": entries,
    }


def analyze_sentence_sync(nlp: Language, text: str) -> dict:
    doc = nlp(text)
    return {
        "text": text,
        "tokens": [
            _token_to_dict(t) for t in doc if not (t.is_punct or t.is_space)
        ],
    }


def analyze_word_sync(
    nlp: Language, form: str, pos: str | None = None
) -> dict:
    """Look up a word form. If pos is given (e.g., carried over from an
    upstream sentence annotation), mark matching entries so the UI can
    highlight the preferred sense — entries are not filtered."""
    doc = nlp(form)
    token = next((t for t in doc if not (t.is_punct or t.is_space)), None)
    if token is None:
        return {"form": form, "normalized": form.lower(), "analyses": []}
    return {
        "form": form,
        "normalized": token.text.lower(),
        "analyses": _annotate_senses(_filter_entries(token._.lexicon), pos),
    }


def analyze_paradigm_sync(nlp: Language, lemma: str, pos: str | None = None) -> dict:
    """Run lemma through pipeline to generate full paradigm(s).

    The URL slug may itself be an inflected form (e.g. ``fuerint``); the
    response distinguishes ``query`` (what the user typed) from ``lemma``
    (the canonical form the pipeline resolved to).

    A single lemma can correspond to multiple distinct verbs (homonyms)
    sharing a headword but with different principal parts and therefore
    different conjugations — e.g. ``dico`` is both ``dicere`` (3rd conj,
    "say") and ``dicare`` (1st conj, "dedicate"). The library lumps all
    of their forms together; here we group lexicon entries by principal
    parts and emit one paradigm per group so the template can render
    them independently.
    """
    doc = nlp(lemma)
    token = next((t for t in doc if not (t.is_punct or t.is_space)), None)
    if token is None:
        return {"lemma": lemma, "query": lemma, "pos": pos, "paradigms": []}
    resolved = token.lemma_ or lemma

    forms = _paradigm_forms(token, pos)
    # Restrict to entries whose headword matches the resolved lemma —
    # ``token._.lexicon`` includes any entry where the surface form is
    # found, so for `sum` we'd otherwise pull in `sumo` and placeholder
    # rows. Keep only the ones that actually share the lemma.
    candidates = [
        e for e in (_filter_entries(token._.lexicon) or [])
        if e.get("headword") == resolved
    ]
    # The spaCy paradigm_generator constrains generation to ``token.pos_``
    # (e.g. ``cura`` may be tagged VERB out of context, but its lexicon
    # entries are nouns — the verb constraint then yields zero forms).
    # When the generator returns empty but the lexicon has lemma-matched
    # candidates, regenerate without the POS constraint so the noun (or
    # other) reading still surfaces.
    if not forms and candidates:
        forms = _regenerate_unfiltered(nlp, resolved, pos)
    paradigms = _group_paradigms(candidates, forms, pos)
    # Prefer the gloss that matches the rendered paradigm: find the
    # first form in any paradigm group whose surface equals the query
    # slug, and use its feats. Falls back to the tagger's morph when
    # the slug doesn't appear in the paradigm (e.g. unknown lemma).
    # Avoids mismatches like /paradigm/cura showing the noun table but
    # reporting "2nd person singular imperative" because the lg tagger
    # picked the verb reading out of context.
    query_morph: dict = {}
    for p in paradigms:
        for f in p.get("forms", []):
            if f.get("form") == lemma:
                query_morph = f.get("feats") or {}
                break
        if query_morph:
            break
    if not query_morph and token.morph:
        query_morph = token.morph.to_dict()
    query_gloss = morph_to_textbook(query_morph)
    return {
        "lemma": resolved,
        "query": lemma,
        "pos": pos,
        "query_morph": query_morph,
        "query_gloss": query_gloss,
        "paradigms": paradigms,
        # Top-level ``forms`` and ``entry`` retained for API consumers
        # that expect the pre-multi-paradigm shape; they reflect the
        # first paradigm group.
        "forms": forms,
        "entry": paradigms[0]["entry"] if paradigms else None,
    }


def _paradigm_forms(token, pos: str | None) -> list[dict]:
    out = []
    for f in token._.paradigm or []:
        if isinstance(f, dict):
            form_val = f.get("form")
            feats = f.get("feats") or {}
            upos = f.get("upos")
        else:
            form_val = f.form
            feats = f.feats or {}
            upos = f.upos
        if isinstance(feats, str):
            feats = dict(kv.split("=", 1) for kv in feats.split("|") if "=" in kv)
        if pos and upos != pos:
            continue
        out.append({"form": form_val, "upos": upos, "feats": feats})
    return out


def _regenerate_unfiltered(nlp: Language, lemma: str, pos: str | None) -> list[dict]:
    """Bypass the spaCy component's tag-driven POS constraint and generate
    forms for *lemma* across all matching POSes. Returns the same shape as
    ``_paradigm_forms`` (list of {form, upos, feats}), filtered by *pos*
    if a query param was supplied. Returns empty list on any failure
    (component missing, generator unloaded, etc.) — caller falls through
    to the normal empty-paradigm rendering.
    """
    try:
        component = nlp.get_pipe("paradigm_generator")
        gen = getattr(component, "_generator", None)
        if gen is None:
            return []
        raw = gen.generate(lemma)
    except (KeyError, ValueError, AttributeError):
        return []
    out = []
    for f in raw:
        feats = dict(
            kv.split("=", 1) for kv in (f.feats or "").split("|") if "=" in kv
        )
        if pos and f.upos != pos:
            continue
        out.append({"form": f.form, "upos": f.upos, "feats": feats})
    return out


def _group_paradigms(
    candidates: list[dict] | None, forms: list[dict], pos: str | None
) -> list[dict]:
    """Group lexicon entries by ``principal_parts`` so homonyms with
    different conjugations get separate paradigms. Within a group we
    merge the glosses from each entry. Returns at least one paradigm
    even when no lexicon entry was found (with ``entry=None``).

    For non-verb groups, additionally collapse groups whose form-sets
    are byte-identical: indeclinables like ``cum`` get split into
    separate principal-parts groups (e.g. CCONJ + ADV) but render an
    identical table for each, which is just visual duplication for the
    user. Verb groups are exempt — ``_layout_verb`` filters the shared
    forms list per-entry, so two verb groups can render different
    tables from the same data.
    """
    if pos and candidates:
        candidates = [e for e in candidates if pos in (e.get("ud_pos") or [])]
    if not candidates:
        return [{"entry": None, "extra_glosses": [], "forms": forms}]
    by_pp: dict[tuple, dict] = {}
    order: list[tuple] = []
    for e in candidates:
        pp_key = tuple(e.get("principal_parts") or [])
        if pp_key not in by_pp:
            by_pp[pp_key] = {"entry": e, "extra_glosses": [], "forms": forms}
            order.append(pp_key)
        else:
            extra = (e.get("glosses") or [])[:1]
            by_pp[pp_key]["extra_glosses"].extend(extra)
    groups = [by_pp[k] for k in order]
    if len(groups) <= 1:
        return groups
    if any(_has_verb_pos(g["entry"]) for g in groups):
        return groups
    by_form: dict[tuple, dict] = {}
    out: list[dict] = []
    for g in groups:
        form_key = tuple(
            (f.get("form"), f.get("upos"), tuple(sorted((f.get("feats") or {}).items())))
            for f in g["forms"]
        )
        if form_key in by_form:
            existing = by_form[form_key]
            extra = (g["entry"].get("glosses") or [])[:1] if g["entry"] else []
            existing["extra_glosses"].extend(extra)
        else:
            by_form[form_key] = g
            out.append(g)
    return out


def _has_verb_pos(entry: dict | None) -> bool:
    if not entry:
        return False
    return any(p in ("VERB", "AUX") for p in (entry.get("ud_pos") or []))


async def analyze_sentence_async(nlp: Language, text: str) -> dict:
    return await asyncio.to_thread(analyze_sentence_sync, nlp, text)


async def analyze_word_async(
    nlp: Language, form: str, pos: str | None = None
) -> dict:
    return await asyncio.to_thread(analyze_word_sync, nlp, form, pos)


async def analyze_paradigm_async(
    nlp: Language, lemma: str, pos: str | None = None
) -> dict:
    return await asyncio.to_thread(analyze_paradigm_sync, nlp, lemma, pos)
