from django.db import models

class ProductVersion(models.Model):
    """Версия продукта (например, 'v1.0 2022', 'v2.0 2024')"""
    name = models.CharField(max_length=50)
    release_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class VisitSession(models.Model):
    """Сессия пользователя (Visit)"""
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    visit_id = models.CharField(max_length=100, unique=True) # ID из метрики
    client_id = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    duration_sec = models.IntegerField(default=0)
    device_category = models.CharField(max_length=50) # mobile/desktop
    source = models.CharField(max_length=100, null=True)
    
    # Метрики сессии
    bounced = models.BooleanField(default=False) # Отказ
    page_views = models.IntegerField(default=0)
    
    # Новые метрики из Yandex Metrica (высокая заполненность)
    browser = models.CharField(max_length=100, null=True)  # из ym:s:browser (99.9%)
    os = models.CharField(max_length=100, null=True)  # из ym:s:operatingSystem (99.9%)
    screen_width = models.IntegerField(null=True)  # из ym:s:screenWidth (100%)
    screen_height = models.IntegerField(null=True)  # из ym:s:screenHeight (100%)
    screen_format = models.CharField(max_length=50, null=True)  # из ym:s:screenFormat (100%)
    is_returning_visitor = models.BooleanField(default=False)  # из !ym:s:isNewUser (100%)
    entry_page = models.CharField(max_length=500, null=True)  # из ym:s:startURL (100%)
    exit_page = models.CharField(max_length=500, null=True)  # из ym:s:endURL (100%)
    traffic_source = models.CharField(max_length=200, null=True)  # из ym:s:lastsignReferalSource (25%, опционально)
    network_type = models.CharField(max_length=50, null=True)  # из ym:s:networkType (42%, опционально)
    
    # Goals достигнутые в этой сессии (для воронок)
    # Список ID целей Yandex Metrica, например: [39566071, 53631805]
    goals_id = models.JSONField(default=list, null=True, blank=True, help_text="Список ID целей, достигнутых в этой сессии")

class PageHit(models.Model):
    """Действие внутри сессии (Hit)"""
    session = models.ForeignKey(VisitSession, related_name='hits', on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    url = models.URLField(max_length=500)
    page_title = models.CharField(max_length=255, null=True)
    action_type = models.CharField(max_length=50, default='view') # view, click, scroll
    
    # Технические координаты (для тепловых карт/rage clicks)
    x_pos = models.IntegerField(null=True)
    y_pos = models.IntegerField(null=True)
    
    # Новые метрики из Yandex Metrica
    time_on_page = models.IntegerField(null=True)  # рассчитывается как разница между hits
    scroll_depth = models.IntegerField(null=True)  # из ym:pv:params если доступно (31%)
    referrer_url = models.CharField(max_length=500, null=True)  # из ym:pv:referer (58%)
    is_exit = models.BooleanField(default=False)  # рассчитывается (последний hit в сессии)
    browser = models.CharField(max_length=100, null=True)  # из ym:pv:browser (99.9%)
    os = models.CharField(max_length=100, null=True)  # из ym:pv:operatingSystem (99.9%)
    screen_width = models.IntegerField(null=True)  # из ym:pv:screenWidth (100%)
    screen_height = models.IntegerField(null=True)  # из ym:pv:screenHeight (100%)
    device_category = models.CharField(max_length=50, null=True)  # из ym:pv:deviceCategory (100%)

class UXIssue(models.Model):
    """Обнаруженная проблема (Результат работы алгоритмов)"""
    
    PROBLEM_TYPES = [
        ('RAGE_CLICK', 'Rage Clicks'),
        ('DEAD_CLICK', 'Dead Clicks'),
        ('LOOPING', 'Navigation Loop'),
        ('FORM_ABANDON', 'Form Abandonment'),
        ('HIGH_BOUNCE', 'High Bounce Rate'),
        ('WANDERING', 'Wandering Users'),  # НОВОЕ
        ('NAVIGATION_BACK', 'Frequent Back Button Usage'),  # НОВОЕ
        ('FORM_FIELD_ERRORS', 'Form Input Errors'),  # НОВОЕ
        ('FUNNEL_DROPOFF', 'Funnel Drop-off Point'),  # НОВОЕ
        ('SCAN_AND_DROP', 'Scan And Drop'),  # быстро проскроллил и ушёл
        ('SEARCH_FAIL', 'Search Fail'),  # поиск не дал результата
    ]
    
    SEVERITY = [
        ('CRITICAL', 'Critical'),
        ('WARNING', 'Warning'),
        ('INFO', 'Info'),
    ]
    
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    issue_type = models.CharField(choices=PROBLEM_TYPES, max_length=50)
    severity = models.CharField(choices=SEVERITY, max_length=20)
    
    description = models.TextField() # Описание: "На кнопке 'Купить' замечены rage clicks"
    location_url = models.CharField(max_length=500) # Где случилось
    
    affected_sessions = models.IntegerField() # Сколько пользователей пострадало
    impact_score = models.FloatField() # Влияние на бизнес (0-10)
    
    # AI Recommendations (Пункт 3.4 ТЗ)
    ai_hypothesis = models.TextField(null=True, blank=True) # Гипотеза от LLM
    ai_solution = models.TextField(null=True, blank=True)   # Решение от LLM
    
    # Routing & context metadata
    detected_version_name = models.CharField(max_length=50, default="")
    trend = models.CharField(max_length=30, default="new")  # new/worse/improved/stable
    priority = models.CharField(max_length=20, default="P2")
    recommended_specialists = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)


class UserCohort(models.Model):
    """Результат кластеризации: Группа пользователей с похожим поведением"""
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE, related_name='cohorts')
    
    # Название от нейросети (например: "Заблудившиеся с мобилок")
    name = models.CharField(max_length=100)
    
    # Метрики этой группы (для графика)
    avg_bounce_rate = models.FloatField()
    avg_duration = models.FloatField()
    users_count = models.IntegerField()
    percentage = models.FloatField() # Доля от всей аудитории (0.0 - 1.0)
    
    # Новые поля для целей
    metrics = models.JSONField(default=dict) # Полные метрики (bounce, duration, depth и т.д.)
    conversion_rates = models.JSONField(default=dict) # {"apply_it_button": 0.05, ...}
    
    # Список client_id пользователей в этой когорте (для анализа воронок)
    member_client_ids = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.percentage*100:.1f}%)"
    
    class Meta:
        indexes = [
            models.Index(fields=['version', 'name']),
        ]

class DailyStat(models.Model):
    """Прекалькулированная статистика по дням для быстрых графиков"""
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    date = models.DateField()
    
    total_sessions = models.IntegerField(default=0)
    total_bounces = models.IntegerField(default=0)
    avg_duration = models.FloatField(default=0.0)
    
    # JSON поле для хранения дополнительных метрик (например, распределение по девайсам)
    # Используем TextField для совместимости, но можно JSONField если Postgres
    extra_data = models.JSONField(default=dict)

    class Meta:
        unique_together = ('version', 'date')

class PageMetrics(models.Model):
    """Агрегированные метрики по страницам"""
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    url = models.CharField(max_length=500, db_index=True)
    page_title = models.CharField(max_length=255, null=True)  # самый частый title для этого URL
    total_views = models.IntegerField()  # всего просмотров
    unique_visitors = models.IntegerField()  # уникальных посетителей
    avg_time_on_page = models.FloatField()  # среднее время на странице (сек)
    bounce_rate = models.FloatField()  # отказы с этой страницы (%)
    exit_rate = models.FloatField()  # процент выходов (%)
    avg_scroll_depth = models.FloatField(null=True)  # средняя глубина прокрутки (0-100)
    dominant_cohort = models.CharField(max_length=100, null=True)  # какая когорта чаще всего
    dominant_device = models.CharField(max_length=50, null=True)  # mobile/desktop/tablet
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('version', 'url')
    
    def __str__(self):
        return f"{self.url} ({self.version.name})"


class ConversionFunnel(models.Model):
    """Воронка конверсии - последовательность шагов для достижения цели"""
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE, related_name='funnels')
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Шаги воронки как JSON
    # Формат: [
    #   {'type': 'goal', 'code': 'it_master_button', 'name': 'Кнопка IT-магистратура'},
    #   {'type': 'url', 'url': '/apply/form', 'name': 'Форма заявки'},
    #   {'type': 'goal', 'code': 'submitted_applications', 'name': 'Отправленные заявки'}
    # ]
    steps = models.JSONField(default=list)
    
    # Настройки расчета
    require_sequence = models.BooleanField(default=True, help_text="Требовать последовательность шагов")
    allow_skip_steps = models.BooleanField(default=False, help_text="Разрешить пропуск шагов")
    
    # Метаданные
    is_preset = models.BooleanField(default=False, help_text="Предустановленная воронка")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.version.name})"
    
    class Meta:
        unique_together = ('version', 'name')
        ordering = ['name']


class FunnelMetrics(models.Model):
    """Кэш рассчитанных метрик воронки"""
    funnel = models.ForeignKey(ConversionFunnel, on_delete=models.CASCADE, related_name='metrics_cache')
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    
    # Метрики воронки (JSON)
    # Формат: {
    #   'total_entered': 1234,
    #   'total_completed': 188,
    #   'overall_conversion': 15.2,
    #   'step_metrics': [...],
    #   'cohort_breakdown': {...},  # опционально
    #   'ai_analysis': '...'  # AI-анализ и рекомендации
    # }
    metrics_json = models.JSONField(default=dict)
    
    # Метаданные расчета
    calculated_at = models.DateTimeField(auto_now=True)
    calculation_duration_sec = models.FloatField(null=True, blank=True)
    
    # Флаг: включена ли разбивка по когортам
    includes_cohorts = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('funnel', 'version', 'includes_cohorts')
        indexes = [
            models.Index(fields=['funnel', 'version']),
        ]
    
    def __str__(self):
        return f"{self.funnel.name} metrics ({self.version.name})"
