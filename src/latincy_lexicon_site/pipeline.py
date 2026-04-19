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


def _token_to_dict(token) -> dict:
    return {
        "text": token.text,
        "lemma": token.lemma_,
        "pos": token.pos_,
        "morph": str(token.morph),
        "entries": _filter_entries(token._.lexicon),
    }


def analyze_sentence_sync(nlp: Language, text: str) -> dict:
    doc = nlp(text)
    return {
        "text": text,
        "tokens": [
            _token_to_dict(t) for t in doc if not (t.is_punct or t.is_space)
        ],
    }


def analyze_word_sync(nlp: Language, form: str) -> dict:
    doc = nlp(form)
    token = next((t for t in doc if not (t.is_punct or t.is_space)), None)
    if token is None:
        return {"form": form, "normalized": form.lower(), "analyses": []}
    return {
        "form": form,
        "normalized": token.text.lower(),
        "analyses": _filter_entries(token._.lexicon),
    }


def analyze_paradigm_sync(nlp: Language, lemma: str, pos: str | None = None) -> dict:
    """Run lemma through pipeline to generate full paradigm."""
    doc = nlp(lemma)
    token = next((t for t in doc if not (t.is_punct or t.is_space)), None)
    if token is None:
        return {"lemma": lemma, "pos": pos, "forms": []}

    paradigm = token._.paradigm or []
    forms = []
    for f in paradigm:
        if isinstance(f, dict):
            form_val = f.get("form")
            feats = f.get("feats") or {}
            upos = f.get("upos")
        else:
            form_val = f.form
            feats = f.feats or {}
            upos = f.upos
        if isinstance(feats, str):
            feats = dict(
                kv.split("=", 1) for kv in feats.split("|") if "=" in kv
            )
        if pos and upos != pos:
            continue
        forms.append({"form": form_val, "upos": upos, "feats": feats})
    return {"lemma": lemma, "pos": pos, "forms": forms}


async def analyze_sentence_async(nlp: Language, text: str) -> dict:
    return await asyncio.to_thread(analyze_sentence_sync, nlp, text)


async def analyze_word_async(nlp: Language, form: str) -> dict:
    return await asyncio.to_thread(analyze_word_sync, nlp, form)


async def analyze_paradigm_async(
    nlp: Language, lemma: str, pos: str | None = None
) -> dict:
    return await asyncio.to_thread(analyze_paradigm_sync, nlp, lemma, pos)
