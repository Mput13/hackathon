# Скрипт для загрузки данных в PowerShell
# Использование: .\ingest_data.ps1

Write-Host "Проверка статуса ингестии..." -ForegroundColor Cyan
docker-compose exec web python manage.py check_ingestion_status

Write-Host "`nНачать загрузку данных? (Y/N)" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq "Y" -or $response -eq "y") {
    Write-Host "`nЗагрузка v1.0 (2022)..." -ForegroundColor Green
    docker-compose exec web python manage.py ingest_data --visits "2022_yandex_metrika_visits.parquet" --hits "2022_yandex_metrika_hits.parquet" --product-version "v1.0 (2022)" --year 2022
    
    Write-Host "`nЗагрузка v2.0 (2024)..." -ForegroundColor Green
    docker-compose exec web python manage.py ingest_data --visits "2024_yandex_metrika_visits.parquet" --hits "2024_yandex_metrika_hits.parquet" --product-version "v2.0 (2024)" --year 2024
    
    Write-Host "`nПроверка результатов..." -ForegroundColor Cyan
    docker-compose exec web python manage.py check_ingestion_status
} else {
    Write-Host "Отменено" -ForegroundColor Red
}


