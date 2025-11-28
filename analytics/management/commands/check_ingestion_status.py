from django.core.management.base import BaseCommand
from django.db.models import Count
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue, DailyStat, UserCohort, PageMetrics


class Command(BaseCommand):
    help = 'Проверяет статус ингестии данных и показывает, на каком этапе остановился процесс'

    def add_arguments(self, parser):
        parser.add_argument('--product-version', type=str, help='Имя версии для проверки (например, "v1.0 (2022)")', default=None)

    def handle(self, *args, **options):
        version_name = options.get('product_version')
        
        if version_name:
            versions = ProductVersion.objects.filter(name=version_name)
        else:
            versions = ProductVersion.objects.all()
        
        if not versions.exists():
            self.stdout.write(self.style.WARNING("⚠️  Версии не найдены в базе данных."))
            return
        
        for version in versions:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS(f"📊 Проверка версии: {version.name} (ID: {version.id})"))
            self.stdout.write("=" * 80)
            
            # 1. Проверка сессий
            sessions_count = VisitSession.objects.filter(version=version).count()
            self.stdout.write(f"  1. VisitSession: {sessions_count} сессий")
            
            # 2. Проверка hits
            hits_count = PageHit.objects.filter(session__version=version).count()
            self.stdout.write(f"  2. PageHit: {hits_count} хитов")
            
            # 3. Проверка page metrics
            page_metrics_count = PageMetrics.objects.filter(version=version).count()
            self.stdout.write(f"  3. PageMetrics: {page_metrics_count} страниц")
            
            # 4. Проверка issues
            issues_count = UXIssue.objects.filter(version=version).count()
            self.stdout.write(f"  4. UXIssue: {issues_count} проблем")
            if issues_count > 0:
                issues_by_type = UXIssue.objects.filter(version=version).values('issue_type').annotate(
                    count=Count('id')
                )
                self.stdout.write("     Типы проблем:")
                for item in issues_by_type:
                    self.stdout.write(f"      - {item['issue_type']}: {item['count']}")
            
            # 5. Проверка когорт
            cohorts_count = UserCohort.objects.filter(version=version).count()
            self.stdout.write(f"  5. UserCohort: {cohorts_count} когорт")
            
            # 6. Проверка daily stats
            daily_stats_count = DailyStat.objects.filter(version=version).count()
            self.stdout.write(f"  6. DailyStat: {daily_stats_count} дней")
            
            # Определение этапа
            self.stdout.write("\n  📍 Этап ингестии:")
            if sessions_count == 0:
                self.stdout.write(self.style.ERROR("     ❌ Не загружены сессии - ингестия не началась или упала на этапе загрузки данных"))
            elif hits_count == 0:
                self.stdout.write(self.style.WARNING("     ⚠️  Загружены сессии, но нет хитов - ингестия упала на этапе обработки hits"))
            elif page_metrics_count == 0:
                self.stdout.write(self.style.WARNING("     ⚠️  Есть сессии и хиты, но нет PageMetrics - ингестия упала на этапе расчета метрик"))
            elif issues_count == 0:
                self.stdout.write(self.style.WARNING("     ⚠️  Данные загружены, но НЕТ ISSUES - ингестия упала на этапе анализа проблем!"))
                self.stdout.write(self.style.ERROR("     🔴 Это основная проблема - анализ issues не был выполнен!"))
            elif cohorts_count == 0:
                self.stdout.write(self.style.WARNING("     ⚠️  Issues найдены, но нет когорт - ингестия упала на этапе сегментации"))
            elif daily_stats_count == 0:
                self.stdout.write(self.style.WARNING("     ⚠️  Почти все готово, но нет daily stats - ингестия упала на последнем этапе"))
            else:
                self.stdout.write(self.style.SUCCESS("     ✅ Ингестия завершена успешно! Все этапы пройдены."))
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("\n💡 Рекомендации:")
        
        # Проверяем все версии
        all_versions = ProductVersion.objects.all()
        for version in all_versions:
            issues_count = UXIssue.objects.filter(version=version).count()
            if issues_count == 0:
                sessions_count = VisitSession.objects.filter(version=version).count()
                hits_count = PageHit.objects.filter(session__version=version).count()
                if sessions_count > 0 and hits_count > 0:
                    self.stdout.write(f"\n  Для версии '{version.name}':")
                    self.stdout.write(f"    - Данные загружены ({sessions_count} сессий, {hits_count} хитов)")
                    self.stdout.write(f"    - Но issues отсутствуют - можно попробовать запустить анализ вручную:")
                    self.stdout.write(f"    docker-compose exec web python manage.py shell -c \"")
                    self.stdout.write(f"    from analytics.management.commands.ingest_data import Command")
                    self.stdout.write(f"    from analytics.models import ProductVersion")
                    self.stdout.write(f"    import pandas as pd")
                    self.stdout.write(f"    version = ProductVersion.objects.get(id={version.id})")
                    self.stdout.write(f"    # Запустить анализ на существующих данных\"")

