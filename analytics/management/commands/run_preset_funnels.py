from django.core.management.base import BaseCommand
from django.core.management import call_command
from analytics.models import ProductVersion
from analytics.management.commands.create_funnels import Command as CreateFunnelsCommand


class Command(BaseCommand):
    help = "Создает предустановленные воронки и сразу считает для них метрики"

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-version',
            dest='product_version',
            type=str,
            help='Название версии продукта (например: "v1.0 (2022)"). Если не указано, обрабатываются все версии.'
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
        by_cohorts = options.get('by_cohorts', False)
        force_recalculate = options.get('force_recalculate', False)

        versions = ProductVersion.objects.all()
        if version_name:
            versions = versions.filter(name=version_name)

        if not versions.exists():
            self.stdout.write(self.style.ERROR("Версия не найдена"))
            return

        for version in versions:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n>>> {version.name}"))
            # 1. Создаем пресетные воронки
            self.stdout.write("Создание предустановленных воронок...")
            call_command('create_funnels', product_version=version.name)
            # 2. Считаем метрики
            self.stdout.write("Расчет метрик воронок...")
            call_command(
                'calculate_funnels',
                product_version=version.name,
                by_cohorts=by_cohorts,
                force_recalculate=force_recalculate
            )
        self.stdout.write(self.style.SUCCESS("\nГотово: пресетные воронки созданы и посчитаны."))
