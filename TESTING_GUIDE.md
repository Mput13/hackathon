# ИНСТРУКЦИЯ ПО ТЕСТИРОВАНИЮ НОВЫХ МЕТРИК И ISSUES

## Что было реализовано

### ✅ 1. Расширение моделей данных
- **VisitSession**: добавлены browser, os, screen_width/height, is_returning_visitor, entry_page, exit_page
- **PageHit**: добавлены time_on_page, scroll_depth, referrer_url, is_exit, browser, os, device_category
- **PageMetrics**: новая модель для агрегированных метрик по страницам
- **UXIssue.PROBLEM_TYPES**: добавлены 4 новых типа (WANDERING, NAVIGATION_BACK, FORM_FIELD_ERRORS, FUNNEL_DROPOFF)

### ✅ 2. Извлечение данных
- Обновлены списки колонок для чтения из Parquet
- Добавлена обработка с проверкой наличия полей

### ✅ 3. Расчет метрик
- `calculate_time_on_page()` - рассчитывает время на странице
- `calculate_page_metrics()` - агрегирует метрики по страницам
- `update_page_metrics_cohorts()` - связывает когорты со страницами

### ✅ 4. Новые детекторы issues
- WANDERING, NAVIGATION_BACK, FORM_FIELD_ERRORS, FUNNEL_DROPOFF

### ✅ 5. Улучшение AI
- Обновлена функция `analyze_issue_with_ai()` с новыми параметрами
- Добавлен контекст для приемной комиссии

---

## Как протестировать

### Шаг 1: Проверка миграций

```bash
# Убедитесь, что миграция применена
docker-compose exec web python manage.py showmigrations analytics
```

Должна быть миграция `0003_pagehit_browser_pagehit_device_category_and_more` со статусом `[X]`.

### Шаг 2: Загрузка данных (если еще не загружены)

```bash
# Загрузка версии 2022
docker-compose exec web python manage.py ingest_data \
    --visits "2022_yandex_metrika_visits.parquet" \
    --hits "2022_yandex_metrika_hits.parquet" \
    --product-version "v1.0 (2022)" \
    --year 2022

# Загрузка версии 2024
docker-compose exec web python manage.py ingest_data \
    --visits "2024_yandex_metrika_visits.parquet" \
    --hits "2024_yandex_metrika_hits.parquet" \
    --product-version "v2.0 (2024)" \
    --year 2024
```

**Что проверить в выводе:**
- ✅ "Calculating time_on_page and exit flags..." - должно появиться
- ✅ "Calculating page metrics..." - должно появиться
- ✅ "Updated dominant_cohort for page metrics." - должно появиться
- ✅ "Detected X UX issues." - должно быть больше, чем раньше (добавились новые типы)

### Шаг 3: Проверка новых полей в БД

```bash
# Зайти в Django shell
docker-compose exec web python manage.py shell
```

В shell выполните:

```python
from analytics.models import VisitSession, PageHit, PageMetrics, UXIssue

# Проверка VisitSession
vs = VisitSession.objects.first()
print(f"Browser: {vs.browser}")
print(f"OS: {vs.os}")
print(f"Screen: {vs.screen_width}x{vs.screen_height}")
print(f"Is returning: {vs.is_returning_visitor}")
print(f"Entry page: {vs.entry_page}")
print(f"Exit page: {vs.exit_page}")

# Проверка PageHit
ph = PageHit.objects.first()
print(f"Time on page: {ph.time_on_page}")
print(f"Is exit: {ph.is_exit}")
print(f"Referrer: {ph.referrer_url}")
print(f"Browser: {ph.browser}")
print(f"Device: {ph.device_category}")

# Проверка PageMetrics
pm = PageMetrics.objects.first()
print(f"URL: {pm.url}")
print(f"Page title: {pm.page_title}")
print(f"Avg time: {pm.avg_time_on_page}")
print(f"Exit rate: {pm.exit_rate}")
print(f"Dominant device: {pm.dominant_device}")
print(f"Dominant cohort: {pm.dominant_cohort}")

# Проверка новых типов issues
new_issues = UXIssue.objects.filter(
    issue_type__in=['WANDERING', 'NAVIGATION_BACK', 'FORM_FIELD_ERRORS', 'FUNNEL_DROPOFF']
)
print(f"Найдено новых issues: {new_issues.count()}")
for issue in new_issues[:5]:
    print(f"  - {issue.issue_type}: {issue.location_url} (AI: {issue.ai_hypothesis[:50]}...)")
```

### Шаг 4: Проверка через веб-интерфейс

1. Откройте http://localhost:8000
2. Перейдите в **Issues** (`/issues/`)
3. В фильтре по типу проблемы должны появиться новые опции:
   - Wandering Users
   - Frequent Back Button Usage
   - Form Input Errors
   - Funnel Drop-off Point

4. Проверьте, что AI-гипотезы содержат более детальную информацию (page_title, метрики)

### Шаг 5: Проверка AI-контекста

```bash
# Запустить тестовый скрипт
docker-compose exec web python test_ai_yandex.py
```

Должен вернуть ответ от YandexGPT (не стаб).

### Шаг 6: Проверка метрик страниц

```python
# В Django shell
from analytics.models import PageMetrics

# Проверить, что метрики рассчитаны
pm_count = PageMetrics.objects.count()
print(f"Всего страниц с метриками: {pm_count}")

# Проверить конкретную страницу
pm = PageMetrics.objects.filter(page_title__isnull=False).first()
if pm:
    print(f"Пример страницы: {pm.page_title}")
    print(f"  URL: {pm.url}")
    print(f"  Просмотров: {pm.total_views}")
    print(f"  Среднее время: {pm.avg_time_on_page:.1f} сек")
    print(f"  Exit rate: {pm.exit_rate:.1f}%")
    print(f"  Доминирующее устройство: {pm.dominant_device}")
```

### Шаг 7: Проверка новых детекторов

```python
# В Django shell
from analytics.models import UXIssue

# Проверить каждый новый тип
for issue_type in ['WANDERING', 'NAVIGATION_BACK', 'FORM_FIELD_ERRORS', 'FUNNEL_DROPOFF']:
    count = UXIssue.objects.filter(issue_type=issue_type).count()
    print(f"{issue_type}: {count} issues")
    
    if count > 0:
        example = UXIssue.objects.filter(issue_type=issue_type).first()
        print(f"  Пример: {example.location_url}")
        print(f"  AI гипотеза: {example.ai_hypothesis[:100]}...")
```

---

## Ожидаемые результаты

### После загрузки данных вы должны увидеть:

1. **В логах ingest_data:**
   - "Calculating time_on_page and exit flags..."
   - "Updated X hits with time_on_page and exit flags."
   - "Calculating page metrics..."
   - "Calculated metrics for X pages."
   - "Updated dominant_cohort for page metrics."
   - "Detected X UX issues." (больше, чем раньше)

2. **В базе данных:**
   - VisitSession с заполненными browser, os, entry_page, exit_page
   - PageHit с заполненными time_on_page, is_exit, browser, device_category
   - PageMetrics для каждой уникальной страницы
   - UXIssue с новыми типами (WANDERING, NAVIGATION_BACK, FORM_FIELD_ERRORS, FUNNEL_DROPOFF)

3. **В AI-ответах:**
   - Более детальные гипотезы с упоминанием page_title
   - Контекст про приемную комиссию
   - Упоминание метрик (время на странице, exit_rate)

---

## Возможные проблемы и решения

### Проблема: "Column not found" при загрузке
**Решение:** Это нормально для старых экспортов. Код автоматически пропустит отсутствующие колонки.

### Проблема: time_on_page = None для всех hits
**Решение:** Проверьте, что hits отсортированы правильно. Функция calculate_time_on_page должна быть вызвана после bulk_create.

### Проблема: PageMetrics пустые
**Решение:** Убедитесь, что calculate_page_metrics вызывается после calculate_time_on_page.

### Проблема: Новые issues не находятся
**Решение:** Проверьте, что в данных есть соответствующие паттерны:
- WANDERING: нужны сессии с >10 pageViews без goals
- NAVIGATION_BACK: нужны паттерны возврата
- FORM_FIELD_ERRORS: нужны страницы с /form, /apply в URL
- FUNNEL_DROPOFF: нужны переходы между шагами воронки

---

## Быстрая проверка (1 минута)

```bash
# Запустить загрузку на небольшом наборе данных
docker-compose exec web python manage.py ingest_data \
    --visits "2024_yandex_metrika_visits.parquet" \
    --hits "2024_yandex_metrika_hits.parquet" \
    --product-version "v2.0 (2024) Test" \
    --year 2024

# Проверить результаты
docker-compose exec web python manage.py shell -c "
from analytics.models import *
print('VisitSession с новыми полями:', VisitSession.objects.exclude(browser__isnull=True).count())
print('PageHit с time_on_page:', PageHit.objects.exclude(time_on_page__isnull=True).count())
print('PageMetrics создано:', PageMetrics.objects.count())
print('Новые issues:', UXIssue.objects.filter(issue_type__in=['WANDERING', 'NAVIGATION_BACK', 'FORM_FIELD_ERRORS', 'FUNNEL_DROPOFF']).count())
"
```

Если все числа > 0, значит все работает! 🎉


