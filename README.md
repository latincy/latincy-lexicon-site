# latincy-lexicon-site

FastAPI lookup service for Latin dictionary entries, sentence analysis, and inflectional paradigms. **Status: pre-deploy.** Planned target: `lexicon.exploratoryphilology.org`.

Built on [`latincy-lexicon`](https://github.com/latincy/latincy-lexicon) + [LatinCy](https://huggingface.co/latincy). `latincy-lexicon` builds on William Whitaker's [Words](https://mk270.github.io/whitakers-words/).

## Local development

```bash
uv sync --extra dev --extra models
uv run uvicorn latincy_lexicon_site.main:app --reload
```

Visit http://localhost:8000/docs for API documentation.

## API

- `GET /api/v1/sentence?text=<latin>` — token-level analysis (first 50 words; longer inputs truncate with a notice)
- `GET /api/v1/word/{form}` — dictionary entries for any form
- `GET /api/v1/paradigm/{lemma}?pos=<upos>` — full inflectional table

## Deployment

See `deploy/setup.md` for droplet rebuild runbook.

## License

MIT
