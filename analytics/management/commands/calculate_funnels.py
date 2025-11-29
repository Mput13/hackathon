"""
Management command для расчета метрик воронок конверсии
Запускается отдельно от ingest, не влияет на производительность загрузки данных
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import ProductVersion, ConversionFunnel, FunnelMetrics
from analytics.funnel_utils import calculate_funnel_metrics, calculate_funnel_metrics_by_cohorts, GoalParser
from analytics.ai_service import analyze_funnel_with_ai
import time


class Command(BaseCommand):
    help = 'Рассчитывает метрики воронок конверсии для указанной версии'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-version',
            dest='product_version',
            type=str,
            required=True,
            help='Название версии продукта (например: "v1.0 (2022)")'
        )
        parser.add_argument(
            '--funnel-id',
            type=int,
            help='ID конкретной воронки (если не указан, рассчитываются все воронки версии)'
        )
        parser.add_argument(
            '--by-cohorts',
            action='store_true',
            help='Рассчитать разбивку метрик по когортам'
        )
        parser.add_argument(
            '--force-recalculate',
            action='store_true',
            help='Пересчитать метрики даже если есть кэш'
        )

    def handle(self, *args, **options):
        version_name = options.get('product_version')
        
        funnel_id = options.get('funnel_id')
        by_cohorts = options.get('by_cohorts', False)
        force_recalculate = options.get('force_recalculate', False)
        
        # Получаем версию
        try:
            version = ProductVersion.objects.get(name=version_name)
        except ProductVersion.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Версия "{version_name}" не найдена'))
            return
        
        # Получаем воронки
        funnels_query = ConversionFunnel.objects.filter(version=version)
        if funnel_id:
            funnels_query = funnels_query.filter(id=funnel_id)
        
        funnels = funnels_query.all()
        
        if not funnels.exists():
            self.stdout.write(self.style.WARNING(f'Воронки для версии "{version_name}" не найдены'))
            self.stdout.write(self.style.SUCCESS('Используйте команду create_funnels для создания воронок'))
            return
        
        self.stdout.write(f'Найдено воронок: {funnels.count()}')
        
        goal_parser = GoalParser()
        
        # Рассчитываем метрики для каждой воронки
        for funnel in funnels:
            self.stdout.write(f'\n📊 Рассчитываю метрики для воронки: "{funnel.name}"...')
            
            start_time = time.time()
            
            # Проверяем кэш
            if not force_recalculate:
                cached_metrics = FunnelMetrics.objects.filter(
                    funnel=funnel,
                    version=version,
                    includes_cohorts=by_cohorts
                ).first()
                
                if cached_metrics:
                    # Проверяем свежесть кэша (24 часа)
                    age_hours = (timezone.now() - cached_metrics.calculated_at).total_seconds() / 3600
                    if age_hours < 24:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Используется кэш (возраст: {age_hours:.1f} часов)'
                            )
                        )
                        continue
            
            # Рассчитываем базовые метрики
            try:
                metrics = calculate_funnel_metrics(
                    funnel=funnel,
                    version=version,
                    goal_parser=goal_parser
                )
                
                # Генерируем AI-анализ для воронки
                self.stdout.write('  🤖 Генерирую AI-анализ...')
                ai_analysis = analyze_funnel_with_ai(
                    funnel_name=funnel.name,
                    step_metrics=metrics.get('step_metrics', []),
                    overall_conversion=metrics.get('overall_conversion', 0)
                )
                metrics['ai_analysis'] = ai_analysis
                
                # Если нужна разбивка по когортам
                cohort_breakdown = None
                if by_cohorts:
                    self.stdout.write('  📈 Рассчитываю метрики по когортам...')
                    cohort_breakdown = calculate_funnel_metrics_by_cohorts(
                        funnel=funnel,
                        version=version,
                        goal_parser=goal_parser
                    )
                    metrics['cohort_breakdown'] = cohort_breakdown
                    
                    # AI-анализ для каждой когорты
                    for cohort_id, cohort_data in cohort_breakdown.items():
                        cohort_metrics = cohort_data.get('funnel_metrics', {})
                        cohort_conversion = cohort_data.get('conversion_rate', 0)
                        
                        # Генерируем AI-анализ для всех когорт с индивидуальными метриками
                        cohort_ai_analysis = analyze_funnel_with_ai(
                            funnel_name=funnel.name,
                            step_metrics=cohort_metrics.get('step_metrics', []),
                            overall_conversion=cohort_conversion,
                            cohort_name=cohort_data.get('cohort_name')
                        )
                        cohort_data['ai_analysis'] = cohort_ai_analysis
                
                calculation_time = time.time() - start_time
                
                # Сохраняем базовые метрики (без когорт) - всегда
                base_metrics = metrics.copy()
                if 'cohort_breakdown' in base_metrics:
                    # Удаляем разбивку по когортам для базовых метрик
                    del base_metrics['cohort_breakdown']
                
                FunnelMetrics.objects.update_or_create(
                    funnel=funnel,
                    version=version,
                    includes_cohorts=False,
                    defaults={
                        'metrics_json': base_metrics,
                        'calculation_duration_sec': calculation_time
                    }
                )
                
                # Сохраняем метрики с когортами, если они были рассчитаны
                if by_cohorts and cohort_breakdown:
                    FunnelMetrics.objects.update_or_create(
                        funnel=funnel,
                        version=version,
                        includes_cohorts=True,
                        defaults={
                            'metrics_json': metrics,
                            'calculation_duration_sec': calculation_time
                        }
                    )
                
                # Выводим результаты
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Рассчитано за {calculation_time:.2f} сек'
                    )
                )
                self.stdout.write(f'     Входов: {metrics["total_entered"]}')
                self.stdout.write(f'     Завершили: {metrics["total_completed"]}')
                self.stdout.write(f'     Конверсия: {metrics["overall_conversion"]:.2f}%')
                
                if cohort_breakdown:
                    self.stdout.write(f'     Когорт проанализировано: {len(cohort_breakdown)}')
                
                # Показываем проблемные шаги
                for step_metric in metrics.get('step_metrics', []):
                    if step_metric['conversion_from_prev'] < 50:
                        self.stdout.write(
                            self.style.WARNING(
                                f'     ⚠️ Шаг "{step_metric["step_name"]}": '
                                f'конверсия {step_metric["conversion_from_prev"]:.1f}% '
                                f'(потеряно {step_metric["drop_off"]} пользователей)'
                            )
                        )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Ошибка при расчете: {str(e)}')
                )
                import traceback
                self.stdout.write(traceback.format_exc())
                continue
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Расчет метрик воронок завершен для "{version_name}"'))

