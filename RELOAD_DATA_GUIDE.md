# ИНСТРУКЦИЯ ПО ПЕРЕЗАГРУЗКЕ ДАННЫХ

После добавления новых полей и метрик нужно **полностью перезагрузить данные**, чтобы:
- ✅ Заполнились новые поля (browser, os, time_on_page, scroll_depth и т.д.)
- ✅ Рассчитались метрики страниц (PageMetrics)
- ✅ Обнаружились новые типы issues (WANDERING, NAVIGATION_BACK, FORM_FIELD_ERRORS, FUNNEL_DROPOFF)

---

## Вариант 1: Удалить данные через Django shell (рекомендуется)

```bash
# Зайти в Django shell
docker-compose exec web python manage.py shell
```

В shell выполните:

```python
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue, PageMetrics, UserCohort, DailyStat

# Удалить данные для конкретной версии (например, v2.0 (2024))
version_name = "v2.0 (2024)"
version = ProductVersion.objects.filter(name=version_name).first()

if version:
    print(f"Удаление данных для версии: {version_name}")
    
    # Удаляем в правильном порядке (из-за foreign keys)
    UXIssue.objects.filter(version=version).delete()
    PageMetrics.objects.filter(version=version).delete()
    UserCohort.objects.filter(version=version).delete()
    DailyStat.objects.filter(version=version).delete()
    PageHit.objects.filter(session__version=version).delete()
    VisitSession.objects.filter(version=version).delete()
    
    print("✅ Данные удалены!")
else:
    print(f"Версия {version_name} не найдена")

# Или удалить ВСЕ данные (осторожно!)
# VisitSession.objects.all().delete()  # Это удалит все связанные данные каскадно
```

Затем выйдите из shell (`exit()`) и загрузите данные заново:

```bash
docker-compose exec web python manage.py ingest_data \
    --visits "2024_yandex_metrika_visits.parquet" \
    --hits "2024_yandex_metrika_hits.parquet" \
    --product-version "v2.0 (2024)" \
    --year 2024
```

---

## Вариант 2: Удалить через SQL (быстрее для больших объемов)

```bash
# Подключиться к PostgreSQL
docker-compose exec db psql -U postgres -d ux_analytics

# В psql выполнить:
DELETE FROM analytics_uxissue WHERE version_id IN (SELECT id FROM analytics_productversion WHERE name = 'v2.0 (2024)');
DELETE FROM analytics_pagemetrics WHERE version_id IN (SELECT id FROM analytics_productversion WHERE name = 'v2.0 (2024)');
DELETE FROM analytics_usercohort WHERE version_id IN (SELECT id FROM analytics_productversion WHERE name = 'v2.0 (2024)');
DELETE FROM analytics_dailystat WHERE version_id IN (SELECT id FROM analytics_productversion WHERE name = 'v2.0 (2024)');
DELETE FROM analytics_pagehit WHERE session_id IN (SELECT id FROM analytics_visitsession WHERE version_id IN (SELECT id FROM analytics_productversion WHERE name = 'v2.0 (2024)'));
DELETE FROM analytics_visitsession WHERE version_id IN (SELECT id FROM analytics_productversion WHERE name = 'v2.0 (2024)');

# Выйти
\q
```

---

## Вариант 3: Удалить ВСЕ данные и начать с нуля

```bash
# ⚠️ ВНИМАНИЕ: Это удалит ВСЕ данные!

docker-compose exec web python manage.py shell -c "
from analytics.models import *
VisitSession.objects.all().delete()
print('✅ Все данные удалены')
"
```

Затем загрузите данные заново для всех версий.

---

## После перезагрузки проверьте:

```bash
docker-compose exec web python manage.py shell -c "
from analytics.models import *
vs = VisitSession.objects.first()
print('VisitSession с новыми полями:', vs.browser is not None, vs.os is not None)
ph = PageHit.objects.first()
print('PageHit с time_on_page:', ph.time_on_page is not None)
print('PageMetrics создано:', PageMetrics.objects.count())
print('Новые issues:', UXIssue.objects.filter(issue_type__in=['WANDERING', 'NAVIGATION_BACK', 'FORM_FIELD_ERRORS', 'FUNNEL_DROPOFF']).count())
"
```

---

## Быстрая команда для перезагрузки одной версии

Создайте скрипт `reload_version.sh`:

```bash
#!/bin/bash
VERSION_NAME="$1"
YEAR="$2"
VISITS_FILE="$3"
HITS_FILE="$4"

if [ -z "$VERSION_NAME" ] || [ -z "$YEAR" ] || [ -z "$VISITS_FILE" ] || [ -z "$HITS_FILE" ]; then
    echo "Usage: ./reload_version.sh 'v2.0 (2024)' 2024 '2024_yandex_metrika_visits.parquet' '2024_yandex_metrika_hits.parquet'"
    exit 1
fi

echo "Удаление данных для $VERSION_NAME..."
docker-compose exec web python manage.py shell -c "
from analytics.models import *
v = ProductVersion.objects.filter(name='$VERSION_NAME').first()
if v:
    UXIssue.objects.filter(version=v).delete()
    PageMetrics.objects.filter(version=v).delete()
    UserCohort.objects.filter(version=v).delete()
    DailyStat.objects.filter(version=v).delete()
    PageHit.objects.filter(session__version=v).delete()
    VisitSession.objects.filter(version=v).delete()
    print('✅ Данные удалены')
else:
    print('Версия не найдена')
"

echo "Загрузка данных заново..."
docker-compose exec web python manage.py ingest_data \
    --visits "$VISITS_FILE" \
    --hits "$HITS_FILE" \
    --product-version "$VERSION_NAME" \
    --year "$YEAR"

echo "✅ Готово!"
```

Использование:
```bash
chmod +x reload_version.sh
./reload_version.sh "v2.0 (2024)" 2024 "2024_yandex_metrika_visits.parquet" "2024_yandex_metrika_hits.parquet"
```

