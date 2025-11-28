# Диагностика проблем с ингестией и Issues

## Проблема: Issues не отображаются

Если issues не отображаются на странице, это может означать, что:
1. Ингестия данных не была завершена успешно
2. Анализ issues не был выполнен (процесс упал до этого этапа)
3. Issues были созданы, но есть проблема с отображением

## Шаг 1: Проверка статуса ингестии

Запустите команду для проверки текущего состояния:

```bash
docker-compose exec web python manage.py check_ingestion_status
```

Или для конкретной версии:

```bash
docker-compose exec web python manage.py check_ingestion_status --product-version "v1.0 (2022)"
```

Команда покажет:
- Сколько сессий загружено
- Сколько хитов загружено
- Сколько issues создано
- На каком этапе остановилась ингестия

## Шаг 2: Анализ проблемы

### Если данные загружены, но issues = 0

Это означает, что ингестия упала на этапе анализа. Вы можете:

#### Вариант А: Запустить анализ вручную на уже загруженных данных

```bash
docker-compose exec web python manage.py run_analysis_only --product-version "v1.0 (2022)" --clear-existing
```

Эта команда:
- Загрузит данные из базы данных
- Запустит анализ issues
- Создаст проблемы в базе данных

#### Вариант Б: Перезапустить полную ингестию с улучшенным логированием

```bash
docker-compose exec web python manage.py ingest_data \
    --visits "2022_yandex_metrika_visits.parquet" \
    --hits "2022_yandex_metrika_hits.parquet" \
    --product-version "v1.0 (2022)" \
    --year 2022 \
    --clear
```

Теперь в логах вы увидите детальные сообщения на каждом этапе:
- `DEBUG: Visits loaded. Shape: ...`
- `DEBUG: About to run analysis (this creates issues)...`
- `DEBUG: About to save X issues to database...`

### Если процесс падает с "Killed"

Это означает, что процесс был убит системой из-за нехватки памяти (OOM Killer).

**Решения:**
1. Увеличить память для контейнера в `docker-compose.yml`
2. Использовать сэмплирование данных (уже включено для >10000 визитов)
3. Запускать ингестию поэтапно:
   - Сначала загрузить данные (уже сделано)
   - Затем запустить анализ отдельно: `run_analysis_only`

### Если процесс падает с ошибкой

Теперь все ошибки выводятся детально в логи. Проверьте вывод команды для детального traceback.

## Шаг 3: Проверка результатов

После запуска анализа проверьте:

```bash
# Проверить количество issues
docker-compose exec web python manage.py shell -c "
from analytics.models import UXIssue
print(f'Всего issues: {UXIssue.objects.count()}')
print('По версиям:')
for version in UXIssue.objects.values('version__name').annotate(count=Count('id')):
    print(f\"  {version['version__name']}: {version['count']}\")
"
```

## Быстрый путь к решению

1. **Проверьте статус:**
   ```bash
   docker-compose exec web python manage.py check_ingestion_status
   ```

2. **Если данные есть, но issues нет - запустите анализ:**
   ```bash
   docker-compose exec web python manage.py run_analysis_only --product-version "v1.0 (2022)" --clear-existing
   docker-compose exec web python manage.py run_analysis_only --product-version "v2.0 (2024)" --clear-existing
   ```

3. **Проверьте результат в интерфейсе:**
   - Откройте http://localhost:8000/issues/
   - Issues должны появиться

## Новые возможности

### Улучшенное логирование

Теперь команда `ingest_data` выводит детальную информацию на каждом этапе:
- Загрузка данных
- Создание сессий
- Создание хитов
- Расчет метрик
- **Запуск анализа issues** (критический этап)
- Создание когорт
- Расчет статистики

### Диагностические команды

- `check_ingestion_status` - проверка состояния ингестии
- `run_analysis_only` - запуск только анализа на уже загруженных данных

### Автоматический сбор мусора

Добавлены вызовы `gc.collect()` для освобождения памяти между этапами.

## Проблемы и решения

### "Killed" в логах
**Причина:** Нехватка памяти  
**Решение:** 
- Увеличьте память для контейнера
- Или используйте `run_analysis_only` для поэтапной обработки

### "No issues detected"
**Причина:** В данных нет паттернов, которые определяют issues  
**Решение:** Это нормально, если в данных действительно нет проблемных паттернов

### "ERROR in run_analysis"
**Причина:** Ошибка в логике анализа  
**Решение:** Проверьте traceback в логах и убедитесь, что данные загружены корректно

