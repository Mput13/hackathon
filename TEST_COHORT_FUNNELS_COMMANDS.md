# Команды для тестирования воронок по когортам

## 🚀 Быстрый старт

Используйте готовый скрипт:
```powershell
.\TEST_COHORT_FUNNELS.ps1
```

Или выполните команды пошагово:

## 📋 Пошаговое тестирование

### Шаг 1: Проверка наличия когорт

```powershell
docker-compose exec web python manage.py shell -c "
from analytics.models import UserCohort, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
cohorts = UserCohort.objects.filter(version=version)
print(f'Найдено когорт: {cohorts.count()}')
for cohort in cohorts:
    client_ids_count = len(cohort.member_client_ids) if cohort.member_client_ids else 0
    print(f'  - {cohort.name}: {cohort.users_count} пользователей, {client_ids_count} client_ids')
"
```

**Ожидаемый результат:**
- Должны быть когорты с `member_client_ids`
- Если когорт нет, сначала запустите `ingest_data`

### Шаг 2: Тестовый запуск (dry-run)

Показывает, какие воронки будут созданы, без сохранения в БД:

```powershell
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --dry-run `
    --max-funnels-per-cohort 3
```

**Что проверить:**
- ✅ Найдены пути пользователей
- ✅ Обнаружены частые последовательности
- ✅ Созданы конфигурации воронок
- ✅ Названия воронок содержат название когорты

### Шаг 3: Создание воронок для всех когорт

```powershell
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --max-funnels-per-cohort 3 `
    --min-support 3
```

**Параметры:**
- `--max-funnels-per-cohort 3` - максимум 3 воронки на когорту
- `--min-support 3` - минимум 3 пользователя для создания воронки

**Что проверить:**
- ✅ Воронки созданы для когорт
- ✅ Количество созданных воронок соответствует ожиданиям
- ✅ Нет ошибок в выводе

### Шаг 4: Проверка созданных воронок

```powershell
docker-compose exec web python manage.py shell -c "
from analytics.models import ConversionFunnel, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
funnels = ConversionFunnel.objects.filter(
    version=version,
    is_preset=False,
    name__contains=':'
).order_by('name')
print(f'Найдено воронок для когорт: {funnels.count()}')
for funnel in funnels:
    print(f'  - {funnel.name}: {len(funnel.steps)} шагов')
    for i, step in enumerate(funnel.steps, 1):
        step_type = step.get('type', 'unknown')
        step_name = step.get('name', 'Unknown')
        print(f'    {i}. [{step_type}] {step_name}')
"
```

**Ожидаемый результат:**
- Воронки имеют названия вида: `"Название когорты: Шаг 1 → Шаг 2"`
- Каждая воронка содержит минимум 2 шага
- Шаги могут быть типа `url` или `goal`

### Шаг 5: Расчет метрик воронок

```powershell
docker-compose exec web python manage.py calculate_funnels `
    --product-version "v2.0 (2024)" `
    --by-cohorts
```

**Что проверить:**
- ✅ Метрики рассчитаны для всех воронок
- ✅ Есть разбивка по когортам
- ✅ Нет ошибок в расчетах

### Шаг 6: Проверка метрик

```powershell
docker-compose exec web python manage.py shell -c "
from analytics.models import ConversionFunnel, FunnelMetrics, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
funnels = ConversionFunnel.objects.filter(
    version=version,
    is_preset=False,
    name__contains=':'
)
print(f'Воронок с метриками:')
for funnel in funnels:
    metrics = FunnelMetrics.objects.filter(funnel=funnel, version=version, includes_cohorts=True).first()
    if metrics:
        m = metrics.metrics_json
        entered = m.get('total_entered', 0)
        completed = m.get('total_completed', 0)
        conversion = m.get('overall_conversion', 0)
        print(f'  - {funnel.name}:')
        print(f'    Вошло: {entered}, Завершило: {completed}, Конверсия: {conversion}%')
"
```

**Ожидаемый результат:**
- Метрики показывают количество пользователей, вошедших в воронку
- Показывают количество завершивших воронку
- Рассчитана конверсия

## 🔍 Дополнительные проверки

### Проверка одной конкретной когорты

```powershell
# Сначала узнайте ID когорты
docker-compose exec web python manage.py shell -c "
from analytics.models import UserCohort, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
cohorts = UserCohort.objects.filter(version=version)
for cohort in cohorts:
    print(f'ID: {cohort.id}, Название: {cohort.name}')
"

# Затем создайте воронки только для этой когорты
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --cohort-id 1 `
    --dry-run
```

### Проверка деталей воронки

```powershell
docker-compose exec web python manage.py shell -c "
from analytics.models import ConversionFunnel, ProductVersion
import json

version = ProductVersion.objects.get(name='v2.0 (2024)')
funnel = ConversionFunnel.objects.filter(
    version=version,
    is_preset=False,
    name__contains=':'
).first()

if funnel:
    print(f'Воронка: {funnel.name}')
    print(f'Описание: {funnel.description}')
    print(f'Шаги:')
    for i, step in enumerate(funnel.steps, 1):
        print(f'  {i}. {step}')
"
```

### Очистка и пересоздание

```powershell
# Удалить все автоматически созданные воронки для когорт
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --clear-auto `
    --dry-run

# Создать заново
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --max-funnels-per-cohort 5
```

## ⚠️ Решение проблем

### Нет когорт

Если когорты не найдены, сначала создайте их:

```powershell
docker-compose exec web python manage.py ingest_data `
    --visits "2024_yandex_metrika_visits.parquet" `
    --hits "2024_yandex_metrika_hits.parquet" `
    --product-version "v2.0 (2024)" `
    --year 2024
```

### Воронки не создаются

1. **Проверьте наличие данных в когортах:**
```powershell
docker-compose exec web python manage.py shell -c "
from analytics.models import UserCohort, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
cohort = UserCohort.objects.filter(version=version).first()
if cohort:
    print(f'Когорта: {cohort.name}')
    print(f'Пользователей: {cohort.users_count}')
    print(f'Client IDs: {len(cohort.member_client_ids) if cohort.member_client_ids else 0}')
"
```

2. **Уменьшите min-support:**
```powershell
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --min-support 2 `
    --dry-run
```

### Слишком мало воронок

Увеличьте параметры:

```powershell
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --max-funnels-per-cohort 10 `
    --min-support 2 `
    --max-length 6
```

## 📊 Полная проверка работоспособности

```powershell
# 1. Проверка когорт
docker-compose exec web python manage.py shell -c "
from analytics.models import UserCohort, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
print(f'Когорт: {UserCohort.objects.filter(version=version).count()}')
"

# 2. Тестовый запуск
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)" `
    --dry-run

# 3. Создание воронок
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "v2.0 (2024)"

# 4. Расчет метрик
docker-compose exec web python manage.py calculate_funnels `
    --product-version "v2.0 (2024)" `
    --by-cohorts

# 5. Итоговая проверка
docker-compose exec web python manage.py shell -c "
from analytics.models import ConversionFunnel, FunnelMetrics, ProductVersion
version = ProductVersion.objects.get(name='v2.0 (2024)')
funnels = ConversionFunnel.objects.filter(version=version, is_preset=False, name__contains=':')
metrics_count = FunnelMetrics.objects.filter(version=version, includes_cohorts=True).count()
print(f'Воронок для когорт: {funnels.count()}')
print(f'Воронок с метриками: {metrics_count}')
"
```

