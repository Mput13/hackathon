"""
Management command для автоматического создания воронок на основе когорт

ВНИМАНИЕ: Этот функционал временно отключен из-за проблем с данными.
Используйте существующие воронки и анализируйте их по когортам через calculate_funnels --by-cohorts
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'ОТКЛЮЧЕНО: Используйте calculate_funnels --by-cohorts для анализа существующих воронок по когортам'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-version',
            dest='product_version',
            type=str,
            help='Название версии продукта (не используется, команда отключена)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR('=' * 60))
        self.stdout.write(self.style.ERROR('⚠️  ФУНКЦИОНАЛ ВРЕМЕННО ОТКЛЮЧЕН'))
        self.stdout.write(self.style.ERROR('=' * 60))
        self.stdout.write('')
        self.stdout.write('Проблема: Автоматическое создание воронок для когорт не работает')
        self.stdout.write('с текущими данными из-за несоответствия client_id в когортах и сессиях.')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ РЕКОМЕНДУЕМЫЙ ПОДХОД:'))
        self.stdout.write('')
        self.stdout.write('1. Используйте существующие воронки (созданные вручную или через discover_funnels)')
        self.stdout.write('2. Анализируйте их по когортам:')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('   docker-compose exec web python manage.py calculate_funnels \\'))
        self.stdout.write(self.style.SUCCESS('       --product-version "v2.0 (2024)" --by-cohorts'))
        self.stdout.write('')
        self.stdout.write('Это покажет метрики каждой воронки с разбивкой по когортам.')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Для создания новых воронок используйте:'))
        self.stdout.write('   docker-compose exec web python manage.py discover_funnels \\')
        self.stdout.write('       --product-version "v2.0 (2024)"')
        self.stdout.write('')
