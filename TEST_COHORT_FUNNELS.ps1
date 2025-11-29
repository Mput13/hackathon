# Скрипт для тестирования генерации воронок по когортам
# Использование: .\TEST_COHORT_FUNNELS.ps1

$version = "v2.0 (2024)"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Тестирование воронок по когортам" -ForegroundColor Cyan
Write-Host "Версия: $version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Проверка наличия когорт
Write-Host "Шаг 1: Проверка наличия когорт..." -ForegroundColor Yellow
docker-compose exec web python manage.py shell -c "
from analytics.models import UserCohort, ProductVersion
version = ProductVersion.objects.get(name='$version')
cohorts = UserCohort.objects.filter(version=version)
print(f'Найдено когорт: {cohorts.count()}')
for cohort in cohorts:
    client_ids_count = len(cohort.member_client_ids) if cohort.member_client_ids else 0
    print(f'  - {cohort.name}: {cohort.users_count} пользователей, {client_ids_count} client_ids')
"
Write-Host ""

# Шаг 2: Тестовый запуск (dry-run) - показывает что будет создано
Write-Host "Шаг 2: Тестовый запуск (dry-run)..." -ForegroundColor Yellow
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "$version" `
    --dry-run `
    --max-funnels-per-cohort 3
Write-Host ""

# Шаг 3: Создание воронок для всех когорт
Write-Host "Шаг 3: Создание воронок для всех когорт..." -ForegroundColor Yellow
docker-compose exec web python manage.py generate_cohort_funnels `
    --product-version "$version" `
    --max-funnels-per-cohort 3 `
    --min-support 3
Write-Host ""

# Шаг 4: Проверка созданных воронок
Write-Host "Шаг 4: Проверка созданных воронок..." -ForegroundColor Yellow
docker-compose exec web python manage.py shell -c "
from analytics.models import ConversionFunnel, ProductVersion
version = ProductVersion.objects.get(name='$version')
funnels = ConversionFunnel.objects.filter(
    version=version,
    is_preset=False,
    name__contains=':'
).order_by('name')
print(f'Найдено воронок для когорт: {funnels.count()}')
for funnel in funnels[:10]:  # Показываем первые 10
    print(f'  - {funnel.name}: {len(funnel.steps)} шагов')
if funnels.count() > 10:
    print(f'  ... и еще {funnels.count() - 10} воронок')
"
Write-Host ""

# Шаг 5: Расчет метрик воронок с разбивкой по когортам
Write-Host "Шаг 5: Расчет метрик воронок с разбивкой по когортам..." -ForegroundColor Yellow
docker-compose exec web python manage.py calculate_funnels `
    --product-version "$version" `
    --by-cohorts
Write-Host ""

# Шаг 6: Проверка метрик
Write-Host "Шаг 6: Проверка метрик воронок..." -ForegroundColor Yellow
docker-compose exec web python manage.py shell -c "
from analytics.models import ConversionFunnel, FunnelMetrics, ProductVersion
version = ProductVersion.objects.get(name='$version')
funnels = ConversionFunnel.objects.filter(
    version=version,
    is_preset=False,
    name__contains=':'
)
print(f'Воронок с метриками:')
for funnel in funnels[:5]:  # Показываем первые 5
    metrics = FunnelMetrics.objects.filter(funnel=funnel, version=version, includes_cohorts=True).first()
    if metrics:
        m = metrics.metrics_json
        entered = m.get('total_entered', 0)
        completed = m.get('total_completed', 0)
        conversion = m.get('overall_conversion', 0)
        print(f'  - {funnel.name}:')
        print(f'    Вошло: {entered}, Завершило: {completed}, Конверсия: {conversion}%')
"
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Тестирование завершено!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

