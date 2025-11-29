#!/usr/bin/env bash
set -euo pipefail

# Быстрый запуск ingest без Docker для web-приложения (используется только контейнер db).
# Проводит ingest (с UX-анализом внутри), создает preset-воронки и считает их метрики.
# Usage: ./scripts/ingest_fast.sh [--clear]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CLEAR_FLAG=""
if [[ "${1:-}" == "--clear" ]]; then
  CLEAR_FLAG="--clear"
fi

echo "[1/7] Поднимаю Postgres контейнер..."
docker-compose up -d db

echo "[2/7] Подготавливаю venv и зависимости..."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt >/dev/null

echo "[3/7] Экспортирую переменные окружения для прямого подключения к БД..."
export DB_HOST=${DB_HOST:-localhost}
export DB_PORT=${DB_PORT:-5432}
export DB_NAME=${DB_NAME:-postgres}
export DB_USER=${DB_USER:-postgres}
export DB_PASSWORD=${DB_PASSWORD:-postgres}
export INGEST_SAMPLE_LIMIT=0
export AUTO_INGEST=0
export AUTO_FUNNELS=0

# Данные и версии по умолчанию
YEARS=(2022 2024)
VERSIONS=("v1.0 (2022)" "v2.0 (2024)")
VISITS=("2022_yandex_metrika_visits.parquet" "2024_yandex_metrika_visits.parquet")
HITS=("2022_yandex_metrika_hits.parquet" "2024_yandex_metrika_hits.parquet")

echo "[4/7] Прогоняю миграции..."
python manage.py migrate

echo "[5/7] Запускаю ingest для доступных файлов (UX-анализ выполняется внутри ingest)..."
for idx in "${!YEARS[@]}"; do
  vfile="${VISITS[$idx]}"
  hfile="${HITS[$idx]}"
  vname="${VERSIONS[$idx]}"
  if [[ ! -f "$vfile" || ! -f "$hfile" ]]; then
    echo "  ⚠️  Пропуск $vname: нет $vfile или $hfile"
    continue
  fi
  echo "  → $vname"
  python manage.py ingest_data \
    --visits "$vfile" \
    --hits "$hfile" \
    --product-version "$vname" \
    --year "${YEARS[$idx]}" \
    $CLEAR_FLAG
  echo "  ✓ $vname ingest + UX-анализ завершены"

  echo "  → Создаю preset-воронки для $vname..."
  python manage.py create_funnels \
    --product-version "$vname" \
    $CLEAR_FLAG

  echo "  → Считаю метрики воронок (включая когортный разрез) для $vname..."
  python manage.py calculate_funnels \
    --product-version "$vname" \
    --by-cohorts \
    --force-recalculate
  echo "  ✓ Воронки рассчитаны для $vname"
done

echo "[6/7] Проверяю статус..."
python manage.py check_ingestion_status

echo "[7/7] Готово. Если нужно очистить версии/воронки перед загрузкой, добавь флаг --clear."
