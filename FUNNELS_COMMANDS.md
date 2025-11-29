# Команды для работы с воронками

## ⚠️ ВАЖНО: Используйте `--product-version`, НЕ `--version`!

Django резервирует `--version` для вывода версии (5.2.8), поэтому используйте `--product-version`.

## Создание воронок

```powershell
# Для версии 2024
docker-compose exec web python manage.py create_funnels --product-version "v2.0 (2024)" --clear

# Для версии 2022
docker-compose exec web python manage.py create_funnels --product-version "v1.0 (2022)" --clear
```

**Флаг `--clear`** удаляет существующие воронки перед созданием новых.

## Расчет метрик воронок

```powershell
# Базовый расчет (без когорт)
docker-compose exec web python manage.py calculate_funnels --product-version "v2.0 (2024)"

# С разбивкой по когортам
docker-compose exec web python manage.py calculate_funnels --product-version "v2.0 (2024)" --by-cohorts

# Принудительный пересчет (игнорирует кэш)
docker-compose exec web python manage.py calculate_funnels --product-version "v2.0 (2024)" --by-cohorts --force-recalculate
```

## Новые воронки для 2024

Созданы на основе реальных данных:
1. **Поиск рейтингов** - главная → рейтинги (303 hits)
2. **Просмотр списка программ** - главная → список (106 hits)
3. **Информация об экзаменах** - главная → экзамены (79 hits)
4. **Поиск программ base** - главная → base/programs (48+ hits)
5. **Просмотр контактов** - главная → контакты (25 hits)
6. **Иностранные абитуриенты** - главная → foreign-applicants (42 hits)
7. **Просмотр результатов** - главная → results (30 hits)
8. **Бакалавриат (legacy)** - для совместимости с 2022


