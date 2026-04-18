#!/usr/bin/env bash
# Post-deploy smoke test. Usage: ./scripts/smoke.sh [host]
set -euo pipefail

HOST="${1:-https://lexicon.exploratoryphilology.org}"

echo "→ $HOST/healthz"
curl -fsS "$HOST/healthz" | jq .

echo "→ $HOST/api/v1/word/amo"
curl -fsS "$HOST/api/v1/word/amo" | jq '.analyses | length'

echo "→ $HOST/api/v1/sentence"
curl -fsS --get --data-urlencode "text=arma virumque cano" "$HOST/api/v1/sentence" | jq '.tokens | length'

echo "→ $HOST/word/amo"
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" "$HOST/word/amo"

echo "all checks passed."
