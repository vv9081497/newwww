#!/usr/bin/env bash
# kali_api launcher — Shopify gate checker (gunicorn + curl_cffi)
set -euo pipefail
cd "$(dirname "$0")"
export PORT="${PORT:-8090}"
export KALI_API_URL="${KALI_API_URL:-http://127.0.0.1:${PORT}/shopii}"
exec "${GUNICORN:-gunicorn}" \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WORKERS:-4}" \
    --threads "${THREADS:-4}" \
    --timeout 120 \
    --access-logfile - \
    main:app
