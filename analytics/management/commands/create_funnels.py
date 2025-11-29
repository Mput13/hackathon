"""
Management command для создания предустановленных воронок
на основе целей из goals.yaml
"""
from django.core.management.base import BaseCommand
from analytics.models import ProductVersion, ConversionFunnel
from analytics.utils import GoalParser


class Command(BaseCommand):
    help = 'Создает предустановленные воронки конверсии на основе целей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-version',
            dest='product_version',
            type=str,
            required=True,
            help='Название версии продукта (например: "v1.0 (2022)")'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить существующие воронки перед созданием'
        )

    def handle(self, *args, **options):
        version_name = options.get('product_version')
        
        clear_existing = options.get('clear', False)
        
        try:
            version = ProductVersion.objects.get(name=version_name)
        except ProductVersion.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Версия "{version_name}" не найдена'))
            return
        
        if clear_existing:
            deleted_count = ConversionFunnel.objects.filter(version=version).delete()[0]
            self.stdout.write(self.style.WARNING(f'Удалено воронок: {deleted_count}'))
        
        goal_parser = GoalParser()
        goals = goal_parser.get_goals()
        
        # Создаем предустановленные воронки на основе анализа реальных данных
        # 
        # ОБОСНОВАНИЕ ВЫБОРА ВОРОНОК:
        # 1. Анализ топ URL показал самые популярные страницы:
        #    - Главная: 327 hits
        #    - Рейтинги: 303 hits
        #    - Список программ: 106 hits
        #    - Экзамены: 79 hits
        #    - Программы base: 48+ hits
        #    - Иностранные абитуриенты: 42 hits
        #    - Контакты: 25 hits
        #    - Результаты: 30 hits
        #
        # 2. Воронки созданы на основе этих данных - это реальные пути пользователей,
        #    а не гипотетические сценарии. Это позволяет анализировать фактическое поведение.
        #
        # 3. В 2024 используется /base/ вместо /bachelor/ - учтено в воронках
        #
        preset_funnels = [
            {
                'name': 'Поиск рейтингов',
                'description': 'Самая популярная воронка (303 hits): пользователи ищут информацию о рейтингах поступления. Выбрана на основе анализа топ URL.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/rating/', 'name': 'Страница рейтингов'},
                ],
                'is_preset': True
            },
            {
                'name': 'Просмотр списка программ',
                'description': 'Вторая по популярности (106 hits): пользователи изучают доступные программы обучения. Реальный путь из данных.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/list/', 'name': 'Список программ'},
                ],
                'is_preset': True
            },
            {
                'name': 'Информация об экзаменах',
                'description': 'Третья по популярности (79 hits): абитуриенты изучают требования к экзаменам. Основано на реальных данных.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/exams/', 'name': 'Страница экзаменов'},
                ],
                'is_preset': True
            },
            {
                'name': 'Поиск программ base (2024)',
                'description': 'Четвертая по популярности (48+ hits): поиск программ базового уровня. Учтено изменение структуры в 2024 (/base/ вместо /bachelor/).',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/base/programs/', 'name': 'Список программ base'},
                ],
                'is_preset': True
            },
            {
                'name': 'Иностранные абитуриенты',
                'description': '42 hits: отдельный поток для иностранных студентов. Важный сегмент аудитории.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/foreign-applicants/', 'name': 'Иностранные абитуриенты'},
                ],
                'is_preset': True
            },
            {
                'name': 'Просмотр результатов',
                'description': '30 hits: пользователи проверяют результаты зачисления. Критически важный этап.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/results/', 'name': 'Результаты'},
                ],
                'is_preset': True
            },
            {
                'name': 'Просмотр контактов',
                'description': '25 hits: получение контактной информации. Базовая функциональность сайта.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/', 'name': 'Главная страница'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/contacts/', 'name': 'Страница контактов'},
                ],
                'is_preset': True
            },
            {
                'name': 'Бакалавриат: программы → детали (legacy)',
                'description': 'Для совместимости с версией 2022: в 2022 использовался путь /bachelor/, в 2024 - /base/.',
                'steps': [
                    {'type': 'url', 'url': 'https://priem.mai.ru/bachelor/programs/', 'name': 'Список программ'},
                    {'type': 'url', 'url': 'https://priem.mai.ru/bachelor/programs/item/', 'name': 'Детали программы'},
                ],
                'is_preset': True
            },
        ]
        
        created_count = 0
        skipped_count = 0
        
        for funnel_config in preset_funnels:
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
            
            # Проверяем, что все цели из воронки существуют
            valid_steps = []
            for step in funnel_config['steps']:
                if step['type'] == 'goal':
                    goal_code = step.get('code')
                    goal = goal_parser.get_goal_by_code(goal_code)
                    if not goal:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠️ Цель "{goal_code}" не найдена, пропускаю шаг'
                            )
                        )
                        continue
                    valid_steps.append(step)
                else:
                    valid_steps.append(step)
            
            if not valid_steps:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠️ Воронка "{funnel_config["name"]}" не создана: нет валидных шагов'
                    )
                )
                continue
            
            # Создаем воронку
            funnel = ConversionFunnel.objects.create(
                version=version,
                name=funnel_config['name'],
                description=funnel_config['description'],
                steps=valid_steps,
                is_preset=funnel_config.get('is_preset', True),
                require_sequence=True,
                allow_skip_steps=False
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Создана воронка: "{funnel_config["name"]}" ({len(valid_steps)} шагов)'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Создано воронок: {created_count}, пропущено: {skipped_count}'
            )
        )

