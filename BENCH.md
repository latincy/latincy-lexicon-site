# Benchmarks

Cold start = fresh Python process → `load_pipeline()` → `warmup()`.

## la_core_web_sm

### Local dev (M-series Mac)

| Phase | Time |
|---|---|
| `spacy.load` + attach whitakers/paradigm | 1.03s |
| Warmup pass (`arma uirumque cano`) | 1.75s |
| **Total** | **2.77s** |

### Production droplet (1 vCPU, 1 GB RAM)

| Phase | Time |
|---|---|
| `spacy.load` + attach whitakers/paradigm | 23.88s |
| Warmup pass (`arma uirumque cano`) | 5.79s |
| **Total** | **29.67s** |

Above the design doc's 15s target for `/healthz` reachability, but
acceptable: restarts are rare, nginx 502s briefly during warmup, users
don't trigger restarts. Steady-state RAM settles around 495 MB.

## la_core_web_lg (production target)

Pending — current droplet has 961 MB RAM, below the 2 GB floor needed to
load `la_core_web_lg` without OOM. Bench when the droplet is resized or
deployed to a host with ≥2 GB RAM. Design doc target: `<10s cold,
<1s with Plan A warm cache`.

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
