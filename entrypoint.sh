#!/bin/sh
# Entry point: run migrations, optional data ingestion, then start Django
set -e

# Wait for DB if host is specified
if [ -n "${DB_HOST:-}" ]; then
  echo "Waiting for DB ${DB_HOST}:${DB_PORT:-5432}..."
  db_ready=0
  for i in $(seq 1 30); do
    if python - <<'PY'
import os, socket, sys
host = os.environ.get("DB_HOST", "")
port = int(os.environ.get("DB_PORT", "5432"))
s = socket.socket()
s.settimeout(1)
try:
    s.connect((host, port))
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
    then
      echo "DB is up."
      db_ready=1
      break
    fi
    echo "DB not ready, retrying ($i/30)..."
    sleep 1
  done
  if [ "$db_ready" -ne 1 ]; then
    echo "DB is still unreachable after 30 attempts."
  fi
fi

# Apply migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Optional auto-ingest if enabled (default on) and DB is empty
if [ "${AUTO_INGEST:-1}" = "1" ]; then
  if python manage.py shell -c "from analytics.models import VisitSession; import sys; sys.exit(0 if VisitSession.objects.exists() else 1)"; then
    echo "Data already present, skipping auto-ingest."
  else
    ingest() {
      YEAR="$1"; VERSION="$2"; VISITS="$3"; HITS="$4"
      if [ -f "$VISITS" ] && [ -f "$HITS" ]; then
        echo "Ingesting $VERSION ($YEAR)..."
        python manage.py ingest_data \
          --visits "$VISITS" \
          --hits "$HITS" \
          --product-version "$VERSION" \
          --year "$YEAR" || echo "Ingest for $VERSION failed."
      else
        echo "Skip ingest for $VERSION: files $VISITS or $HITS not found."
      fi
    }

    ingest "${INGEST_YEAR_1:-2022}" "${INGEST_VERSION_1:-v1.0 (2022)}" \
      "${INGEST_VISITS_1:-2022_yandex_metrika_visits.parquet}" \
      "${INGEST_HITS_1:-2022_yandex_metrika_hits.parquet}"

    ingest "${INGEST_YEAR_2:-2024}" "${INGEST_VERSION_2:-v2.0 (2024)}" \
      "${INGEST_VISITS_2:-2024_yandex_metrika_visits.parquet}" \
      "${INGEST_HITS_2:-2024_yandex_metrika_hits.parquet}"
  fi
fi

# Auto-create and calculate preset funnels (can be disabled with AUTO_FUNNELS=0)
if [ "${AUTO_FUNNELS:-1}" = "1" ]; then
  echo "Ensuring preset funnels are created and calculated..."
  python manage.py run_preset_funnels || echo "Preset funnels creation/calculation failed (skipping)."
fi

echo "Starting app with command: $*"
exec "$@"
