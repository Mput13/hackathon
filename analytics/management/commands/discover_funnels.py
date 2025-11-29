"""
Management command для автоматического обнаружения воронок
на основе реальных путей пользователей
"""
from django.core.management.base import BaseCommand
from analytics.models import ProductVersion, ConversionFunnel
from analytics.funnel_discovery import discover_funnels


class Command(BaseCommand):
    help = 'Автоматически обнаруживает воронки на основе реальных путей пользователей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-version',
            dest='product_version',
            type=str,
            required=True,
            help='Название версии продукта (например: "v1.0 (2022)")'
        )
        parser.add_argument(
            '--min-support',
            type=int,
            default=15,
            help='Минимальное количество пользователей для создания воронки (по умолчанию: 15)'
        )
        parser.add_argument(
            '--max-funnels',
            type=int,
            default=20,
            help='Максимальное количество воронок для создания (по умолчанию: 20)'
        )
        parser.add_argument(
            '--min-length',
            type=int,
            default=2,
            help='Минимальная длина пути (по умолчанию: 2)'
        )
        parser.add_argument(
            '--max-length',
            type=int,
            default=4,
            help='Максимальная длина пути (по умолчанию: 4)'
        )
        parser.add_argument(
            '--clear-auto',
            action='store_true',
            help='Удалить все автоматически созданные воронки перед обнаружением'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать найденные воронки без создания в БД'
        )
        parser.add_argument(
            '--min-percentage',
            type=float,
            default=0.5,
            help='Минимальный процент пользователей от общего числа (по умолчанию: 0.5%%)'
        )

    def handle(self, *args, **options):
        version_name = options.get('product_version')
        min_support = options.get('min_support', 10)
        max_funnels = options.get('max_funnels', 20)
        min_length = options.get('min_length', 2)
        max_length = options.get('max_length', 4)
        clear_auto = options.get('clear_auto', False)
        dry_run = options.get('dry_run', False)
        
        try:
            version = ProductVersion.objects.get(name=version_name)
        except ProductVersion.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Версия "{version_name}" не найдена'))
            return
        
        self.stdout.write(f'🔍 Анализирую пути пользователей для версии "{version_name}"...')
        self.stdout.write(f'   Параметры: min_support={min_support}, длина пути {min_length}-{max_length}, максимум {max_funnels} воронок')
        
        # Удаляем автоматически созданные воронки, если нужно
        if clear_auto:
            auto_funnels = ConversionFunnel.objects.filter(
                version=version,
                is_preset=False
            )
            deleted_count = auto_funnels.count()
            auto_funnels.delete()
            self.stdout.write(self.style.WARNING(f'   Удалено автоматических воронок: {deleted_count}'))
        
        # Обнаруживаем воронки
        try:
            self.stdout.write('   Извлекаю пути пользователей...')
            min_percentage = options.get('min_percentage', 2.0)
            discovered_funnels, stats = discover_funnels(
                version=version,
                min_support=min_support,
                min_path_length=min_length,
                max_path_length=max_length,
                max_funnels=max_funnels,
                min_percentage=min_percentage
            )
            self.stdout.write('   Анализ завершен.')
            
            # Выводим статистику
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('📊 Статистика:'))
            self.stdout.write(f'   Всего сессий: {stats.get("total_sessions", 0)}')
            if "total_paths_extracted" in stats:
                self.stdout.write(f'   Извлечено путей: {stats["total_paths_extracted"]}')
            if "frequent_sequences_found" in stats:
                self.stdout.write(f'   Найдено частых последовательностей: {stats["frequent_sequences_found"]}')
            if "filtered_sequences" in stats:
                self.stdout.write(f'   После фильтрации избыточных: {stats["filtered_sequences"]}')
            if "final_sequences_after_percentage_filter" in stats:
                self.stdout.write(f'   После фильтрации по минимальному проценту ({min_percentage}%): {stats["final_sequences_after_percentage_filter"]}')
            if "min_support_used" in stats:
                self.stdout.write(f'   Используемый min_support: {stats["min_support_used"]} пользователей')
            self.stdout.write('')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при обнаружении воронок: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return
        
        if not discovered_funnels:
            self.stdout.write(
                self.style.WARNING(
                    f'Воронки не обнаружены. Попробуйте:\n'
                    f'  - Уменьшить --min-support (текущее: {min_support})\n'
                    f'  - Уменьшить --min-percentage (текущее: {min_percentage}%)\n'
                    f'  - Всего сессий: {stats.get("total_sessions", "неизвестно")}'
                )
            )
            return
        
        self.stdout.write(f'\n✅ Найдено воронок: {len(discovered_funnels)}\n')
        
        # Выводим найденные воронки
        for i, funnel_config in enumerate(discovered_funnels, 1):
            percentage = funnel_config.get('percentage', 0)
            self.stdout.write(f'{i}. {funnel_config["name"]}')
            self.stdout.write(f'   Путь: {" → ".join([step["name"] for step in funnel_config["steps"]])}')
            self.stdout.write(f'   Частота: {funnel_config["frequency"]} пользователей ({percentage:.1f}%)')
            self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: воронки не созданы'))
            return
        
        # Создаем воронки в БД
        created_count = 0
        skipped_count = 0
        
        for funnel_config in discovered_funnels:
            # Проверяем, существует ли уже такая воронка
            existing = ConversionFunnel.objects.filter(
                version=version,
                name=funnel_config['name']
            ).first()
            
            if existing:
                self.stdout.write(
                    self.style.WARNING(f'  ⏭ Воронка "{funnel_config["name"]}" уже существует')
                )
                skipped_count += 1
                continue
            
            # Создаем воронку
            funnel = ConversionFunnel.objects.create(
                version=version,
                name=funnel_config['name'],
                description=funnel_config['description'],
                steps=funnel_config['steps'],
                is_preset=False,  # Автоматически созданная
                require_sequence=True,
                allow_skip_steps=False
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Создана воронка: "{funnel_config["name"]}" '
                    f'({len(funnel_config["steps"])} шагов, {funnel_config["frequency"]} пользователей)'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Создано автоматических воронок: {created_count}, пропущено: {skipped_count}'
            )
        )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n💡 Запустите calculate_funnels для расчета метрик новых воронок:'
                )
            )
            self.stdout.write(
                f'   docker-compose exec web python manage.py calculate_funnels '
                f'--product-version "{version_name}" --by-cohorts'
            )

