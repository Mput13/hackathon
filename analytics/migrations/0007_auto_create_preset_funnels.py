from django.db import migrations


def create_preset_funnels(apps, schema_editor):
    ProductVersion = apps.get_model('analytics', 'ProductVersion')
    ConversionFunnel = apps.get_model('analytics', 'ConversionFunnel')
    FunnelMetrics = apps.get_model('analytics', 'FunnelMetrics')

    # Импортируем утилиту расчета напрямую (используем актуальный код проекта)
    from analytics.funnel_utils import calculate_funnel_metrics, GoalParser

    preset_funnels = [
        {
            'name': 'Просмотр контактов',
            'description': 'Воронка просмотра контактов: главная → контакты',
            'steps': [
                {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                {'type': 'url', 'url': 'https://priem.mai.ru/contacts/', 'name': 'Страница контактов'},
            ],
        },
        {
            'name': 'Бакалавриат: программы → детали',
            'description': 'Воронка изучения программ бакалавриата',
            'steps': [
                {'type': 'url', 'url': 'https://priem.mai.ru/bachelor/programs/', 'name': 'Список программ'},
                {'type': 'url', 'url': 'https://priem.mai.ru/bachelor/programs/item/', 'name': 'Детали программы'},
            ],
        },
        {
            'name': 'Поиск рейтингов',
            'description': 'Воронка поиска рейтингов',
            'steps': [
                {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                {'type': 'url', 'url': 'https://priem.mai.ru/rating/', 'name': 'Страница рейтингов'},
            ],
        },
        {
            'name': 'Просмотр контактов (URL-based goal)',
            'description': 'Воронка через URL-based цель contacts_view',
            'steps': [
                {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                {'type': 'goal', 'code': 'contacts_view', 'name': 'Просмотр контактов (url_prefix goal)'},
            ],
        },
    ]

    goal_parser = GoalParser()

    for version in ProductVersion.objects.all():
        for cfg in preset_funnels:
            funnel, created = ConversionFunnel.objects.get_or_create(
                version=version,
                name=cfg['name'],
                defaults={
                    'description': cfg.get('description', ''),
                    'steps': cfg.get('steps', []),
                    'is_preset': True,
                    'require_sequence': True,
                    'allow_skip_steps': False,
                },
            )
            # Если данные уже загружены — сразу считаем метрики для пресета
            if created:
                try:
                    metrics = calculate_funnel_metrics(
                        funnel=funnel,
                        version=version,
                        goal_parser=goal_parser
                    )
                    FunnelMetrics.objects.update_or_create(
                        funnel=funnel,
                        version=version,
                        includes_cohorts=False,
                        defaults={'metrics_json': metrics}
                    )
                except Exception:
                    # Не блокируем миграцию, если нет данных или случилась ошибка расчета
                    continue


def delete_preset_funnels(apps, schema_editor):
    ProductVersion = apps.get_model('analytics', 'ProductVersion')
    ConversionFunnel = apps.get_model('analytics', 'ConversionFunnel')

    preset_names = [
        'Просмотр контактов',
        'Бакалавриат: программы → детали',
        'Поиск рейтингов',
        'Просмотр контактов (URL-based goal)',
    ]
    ConversionFunnel.objects.filter(
        version__in=ProductVersion.objects.all(),
        name__in=preset_names,
        is_preset=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0006_visitsession_goals_id'),
    ]

    operations = [
        migrations.RunPython(create_preset_funnels, reverse_code=delete_preset_funnels),
    ]
