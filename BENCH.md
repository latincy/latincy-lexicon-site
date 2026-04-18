# Benchmarks

Cold start = fresh Python process → `load_pipeline()` → `warmup()`.

## la_core_web_sm (CI + local dev)

| Phase | Time |
|---|---|
| `spacy.load` + attach whitakers/paradigm | 1.03s |
| Warmup pass (`arma uirumque cano`) | 1.75s |
| **Total** | **2.77s** |

Well under the design doc's 15s target for `/healthz` to become reachable
after `systemctl start`.

## la_core_web_lg (production)

Pending — bench on the droplet after first deploy and record here. The
design doc flags `<10s cold, <1s with Plan A warm cache` as the target.

## How to re-run

```bash
uv run python -c "
from latincy_lexicon_site.pipeline import load_pipeline, warmup
import time
t0 = time.perf_counter()
nlp = load_pipeline('la_core_web_sm')  # or la_core_web_lg
t1 = time.perf_counter()
warmup(nlp)
t2 = time.perf_counter()
print(f'load={t1-t0:.2f}s warmup={t2-t1:.2f}s total={t2-t0:.2f}s')
"
```
