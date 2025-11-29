"""
Команда для запуска только анализа issues на уже загруженных данных.
Используется, когда данные загружены, но анализ не был выполнен.
"""
import pandas as pd
from django.core.management.base import BaseCommand
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue
from analytics.management.commands.ingest_data import Command as IngestCommand
import traceback
import sys


class Command(BaseCommand):
    help = 'Запускает только анализ issues на уже загруженных данных (без перезагрузки)'

    def add_arguments(self, parser):
        parser.add_argument('--product-version', type=str, help='Имя версии (например, "v1.0 (2022)")', required=True)
        parser.add_argument('--clear-existing', action='store_true', help='Удалить существующие issues перед анализом')

    def handle(self, *args, **options):
        version_name = options['product_version']
        
        try:
            version = ProductVersion.objects.get(name=version_name)
        except ProductVersion.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Версия '{version_name}' не найдена в базе данных."))
            return
        
        self.stdout.write(f"📊 Запуск анализа для версии: {version.name} (ID: {version.id})")
        
        # Проверяем наличие данных
        sessions_count = VisitSession.objects.filter(version=version).count()
        hits_count = PageHit.objects.filter(session__version=version).count()
        
        if sessions_count == 0:
            self.stdout.write(self.style.ERROR("❌ Нет сессий для этой версии. Сначала загрузите данные через ingest_data."))
            return
        
        if hits_count == 0:
            self.stdout.write(self.style.ERROR("❌ Нет хитов для этой версии. Сначала загрузите данные через ingest_data."))
            return
        
        self.stdout.write(f"✅ Найдено {sessions_count} сессий и {hits_count} хитов")
        
        # Удаляем существующие issues, если нужно
        if options.get('clear_existing', False):
            deleted_count = UXIssue.objects.filter(version=version).delete()[0]
            self.stdout.write(f"🗑️  Удалено {deleted_count} существующих issues")
        
        # Загружаем данные из БД в DataFrame
        self.stdout.write("📥 Загрузка данных из базы данных...")
        
        # Загружаем visits со всеми необходимыми полями
        visits_qs = VisitSession.objects.filter(version=version).values(
            'visit_id', 'client_id', 'start_time', 'duration_sec', 
            'device_category', 'source', 'bounced', 'page_views',
            'is_returning_visitor', 'entry_page', 'exit_page',
            'browser', 'os', 'screen_width', 'screen_height', 'screen_format',
            'traffic_source', 'network_type'
        )
        
        # Преобразуем в DataFrame с правильными именами колонок
        visits_data = []
        for v in visits_qs:
            visits_data.append({
                'ym:s:visitID': v['visit_id'],
                'ym:s:clientID': v['client_id'],
                'ym:s:dateTime': v['start_time'],
                'ym:s:visitDuration': v['duration_sec'],
                'ym:s:deviceCategory': v['device_category'],
                'ym:s:referer': v['source'] or '',
                'ym:s:bounce': 1 if v['bounced'] else 0,
                'ym:s:pageViews': v['page_views'],
                'ym:s:startURL': v['entry_page'] or '',
                'ym:s:endURL': v['exit_page'] or '',
                'ym:s:browser': v['browser'],
                'ym:s:operatingSystem': v['os'],
                'ym:s:screenWidth': v['screen_width'],
                'ym:s:screenHeight': v['screen_height'],
                'ym:s:screenFormat': v['screen_format'],
                'ym:s:lastsignReferalSource': v['traffic_source'],
                'ym:s:networkType': v['network_type'],
                'ym:s:goalsID': None,  # Цели хранятся отдельно, но для анализа можем пропустить
            })
        
        df_visits = pd.DataFrame(visits_data)
        
        # Загружаем hits со всеми необходимыми полями
        hits_qs = PageHit.objects.filter(session__version=version).select_related('session').values(
            'session__client_id', 'timestamp', 'url', 'page_title',
            'referrer_url', 'browser', 'os', 'screen_width', 'screen_height', 'device_category',
            'time_on_page', 'scroll_depth', 'is_exit'
        )
        
        hits_data = []
        for h in hits_qs:
            hits_data.append({
                'ym:pv:clientID': h['session__client_id'],
                'ym:pv:dateTime': h['timestamp'],
                'ym:pv:URL': h['url'],
                'ym:pv:title': h['page_title'],
                'ym:pv:referer': h['referrer_url'],
                'ym:pv:browser': h['browser'],
                'ym:pv:operatingSystem': h['os'],
                'ym:pv:screenWidth': h['screen_width'],
                'ym:pv:screenHeight': h['screen_height'],
                'ym:pv:deviceCategory': h['device_category'],
                'time_on_page': h['time_on_page'],
                'scroll_depth': h['scroll_depth'],
                'is_exit': h['is_exit'],
            })
        
        df_hits = pd.DataFrame(hits_data)
        
        self.stdout.write(f"✅ Загружено: {len(df_visits)} visits, {len(df_hits)} hits")
        
        # Нормализуем client_id
        if not df_visits.empty:
            df_visits['ym:s:clientID'] = df_visits['ym:s:clientID'].astype(str)
            df_visits['client_id_norm'] = df_visits['ym:s:clientID']
        
        if not df_hits.empty:
            df_hits['ym:pv:clientID'] = df_hits['ym:pv:clientID'].astype(str)
            df_hits['client_id_norm'] = df_hits['ym:pv:clientID']
        
        # Запускаем анализ через метод из IngestCommand
        try:
            self.stdout.write("🔍 Запуск анализа issues...")
            ingest_cmd = IngestCommand()
            ingest_cmd.stdout = self.stdout
            
            ingest_cmd.run_analysis(version, df_hits, df_visits)
            
            # Проверяем результат
            issues_count = UXIssue.objects.filter(version=version).count()
            self.stdout.write(self.style.SUCCESS(f"\n✅ Анализ завершен! Создано {issues_count} issues."))
            
        except Exception as e:
            error_msg = f"❌ ОШИБКА при выполнении анализа: {e}\n"
            error_msg += "=" * 80 + "\n"
            error_msg += "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_msg += "=" * 80 + "\n"
            self.stdout.write(self.style.ERROR(error_msg))
            sys.stderr.write(error_msg)
            sys.stderr.flush()
            raise

