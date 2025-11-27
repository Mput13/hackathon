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

class UXIssue(models.Model):
    """Обнаруженная проблема (Результат работы алгоритмов)"""
    
    PROBLEM_TYPES = [
        ('RAGE_CLICK', 'Rage Clicks'),
        ('DEAD_CLICK', 'Dead Clicks'),
        ('LOOPING', 'Navigation Loop'),
        ('FORM_ABANDON', 'Form Abandonment'),
        ('HIGH_BOUNCE', 'High Bounce Rate'),
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
    
    created_at = models.DateTimeField(auto_now_add=True)

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

