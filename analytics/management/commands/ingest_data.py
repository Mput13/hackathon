import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue, DailyStat, UserCohort, PageMetrics, IssueLifecycle
from datetime import datetime, timedelta
import os
import urllib.parse
from analytics.ai_service import analyze_issue_with_ai, generate_cohort_name
from analytics.utils import GoalParser
import traceback
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

MIN_PAGE_VIEWS_FOR_PAGE_ALERT = int(os.environ.get("MIN_PAGE_VIEWS_FOR_PAGE_ALERT", "30"))
MIN_WANDERING_SESSIONS = int(os.environ.get("MIN_WANDERING_SESSIONS", "5"))

class Command(BaseCommand):
    help = 'Ingests Parquet data from Yandex Metrica and runs UX analysis'

    def add_arguments(self, parser):
        parser.add_argument('--visits', type=str, help='Path to visits parquet file')
        parser.add_argument('--hits', type=str, help='Path to hits parquet file')
        parser.add_argument('--product-version', type=str, help='Version name (e.g., "v1.0")')
        parser.add_argument('--year', type=int, help='Year of data (e.g., 2022)')
        parser.add_argument('--clear', action='store_true', help='Clear existing data for this version before loading')

    def handle(self, *args, **options):
        self.stdout.write("DEBUG: Command started")
        
        visits_path = options['visits']
        hits_path = options['hits']
        version_name = options['product_version']
        year = options['year']

        self.stdout.write(f"DEBUG: Args received: {visits_path}, {hits_path}, {version_name}")

        if not visits_path or not hits_path or not version_name:
            self.stdout.write(self.style.ERROR('Please provide --visits, --hits and --product-version'))
            return

        self.stdout.write(f"Starting ingestion for {version_name}...")

        try:
            # 0. Load Goals
            goal_parser = GoalParser()
            goals_config = goal_parser.get_goals()
            self.stdout.write(f"Loaded {len(goals_config)} goals from config.")

            # 1. Create or Get Version
            self.stdout.write("DEBUG: Creating ProductVersion...")
            version, created = ProductVersion.objects.get_or_create(
                name=version_name,
                defaults={'release_date': datetime(year, 1, 1), 'is_active': True}
            )
            self.stdout.write(f"DEBUG: ProductVersion created: {version.id}")
            
            # 1.5. Clear existing data if --clear flag is set
            if options.get('clear', False):
                self.stdout.write(self.style.WARNING(f"Clearing existing data for version {version_name}..."))
                UXIssue.objects.filter(version=version).delete()
                PageMetrics.objects.filter(version=version).delete()
                UserCohort.objects.filter(version=version).delete()
                DailyStat.objects.filter(version=version).delete()
                PageHit.objects.filter(session__version=version).delete()
                VisitSession.objects.filter(version=version).delete()
                self.stdout.write(self.style.SUCCESS("✅ Existing data cleared."))

            # 2. Load Data (Using Pandas)
            self.stdout.write(f"Loading Parquet files from {visits_path}...")
            if not os.path.exists(visits_path):
                 self.stdout.write(self.style.ERROR(f"File not found: {visits_path}"))
                 return
            
            # Visits columns - расширены для новых метрик
            visits_columns = [
                'ym:s:visitID', 'ym:s:clientID', 'ym:s:counterUserIDHash', 'ym:s:dateTime', 
                'ym:s:visitDuration', 'ym:s:deviceCategory', 'ym:s:referer', 
                'ym:s:bounce', 'ym:s:pageViews', 'ym:s:goalsID',
                # Новые поля (100% или >99% заполнено)
                'ym:s:isNewUser',      # 100%
                'ym:s:startURL',       # 100%
                'ym:s:endURL',         # 100%
                'ym:s:browser',        # 99.9%
                'ym:s:operatingSystem', # 99.9%
                'ym:s:screenWidth',    # 100%
                'ym:s:screenHeight',   # 100%
                'ym:s:screenFormat',   # 100%
                # Поля с частичным заполнением (опционально)
                'ym:s:lastsignReferalSource',  # 25%
                'ym:s:networkType',            # 42%
            ] 

            # Пытаемся загрузить все колонки, если какие-то отсутствуют - удаляем их из списка
            try:
                df_visits = pd.read_parquet(visits_path, columns=visits_columns)
            except Exception as e:
                self.stdout.write(f"Warning: Some columns not found, trying to load available ones. Error: {e}")
                # Удаляем опциональные поля и пробуем снова
                optional_fields = ['ym:s:lastsignReferalSource', 'ym:s:networkType', 'ym:s:goalsID']
                for field in optional_fields:
                    if field in visits_columns:
                        visits_columns.remove(field)
                try:
                    df_visits = pd.read_parquet(visits_path, columns=visits_columns)
                except Exception:
                    # Если все еще ошибка, загружаем только базовые поля
                    basic_fields = ['ym:s:visitID', 'ym:s:clientID', 'ym:s:dateTime', 
                                   'ym:s:visitDuration', 'ym:s:deviceCategory', 'ym:s:referer', 
                                   'ym:s:bounce', 'ym:s:pageViews']
                    df_visits = pd.read_parquet(visits_path, columns=basic_fields)
                    self.stdout.write("Warning: Loaded only basic fields due to column mismatch.")

            def normalize_client_id(val):
                """
                Приводит clientID/counterUserIDHash к стабильной строке.
                Учитывает float в научной нотации (часто в hits), чтобы совпадали с int из visits.
                """
                if pd.isna(val):
                    return None
                # Пробуем через float/Decimal, чтобы убрать научную нотацию
                try:
                    # float('1.7e+18') -> 1700000000000000000
                    return f"{float(val):.0f}"
                except Exception:
                    pass
                s = str(val)
                if s.endswith('.0'):
                    s = s[:-2]
                return s

            # Ensure timestamps are timezone-aware (UTC) to avoid Django naive datetime warnings
            df_visits['ym:s:dateTime'] = pd.to_datetime(df_visits['ym:s:dateTime'], utc=True, errors='coerce')
            # Normalize client IDs to consistent strings for joins
            df_visits['client_id_norm'] = df_visits['ym:s:clientID'].apply(normalize_client_id)
            df_visits = df_visits[df_visits['client_id_norm'].notna()]
            df_visits['ym:s:clientID'] = df_visits['client_id_norm']
            # Normalize counterUserIDHash for joins with hits (более надежный ключ)
            if 'ym:s:counterUserIDHash' in df_visits.columns:
                df_visits['counter_user_hash'] = df_visits['ym:s:counterUserIDHash'].apply(normalize_client_id)
            else:
                df_visits['counter_user_hash'] = None
            self.stdout.write(f"DEBUG: Visits loaded. Shape: {df_visits.shape}")
            
            # Hits columns - расширены для новых метрик
            hits_columns = [
                'ym:pv:clientID', 'ym:pv:counterUserIDHash', 'ym:pv:dateTime', 'ym:pv:URL', 
                'ym:pv:title',    # 68% - использовать с проверкой на null
                # Новые поля
                'ym:pv:referer',           # 58%
                'ym:pv:browser',           # 99.9%
                'ym:pv:operatingSystem',   # 99.9%
                'ym:pv:screenWidth',       # 100%
                'ym:pv:screenHeight',      # 100%
                'ym:pv:deviceCategory',    # 100%
                'ym:pv:params',            # 31% - для scroll depth (опционально)
            ]
            try:
                df_hits = pd.read_parquet(hits_path, columns=hits_columns)
            except Exception as e:
                self.stdout.write(f"Warning: Some hit columns not found, trying basic set. Error: {e}")
                # Пробуем загрузить только базовые поля
                basic_hits = ['ym:pv:clientID', 'ym:pv:dateTime', 'ym:pv:URL', 'ym:pv:title']
                df_hits = pd.read_parquet(hits_path, columns=basic_hits)
                self.stdout.write("Warning: Loaded only basic hit fields.")
            df_hits['ym:pv:dateTime'] = pd.to_datetime(df_hits['ym:pv:dateTime'], utc=True, errors='coerce')
            df_hits['client_id_norm'] = df_hits['ym:pv:clientID'].apply(normalize_client_id)
            df_hits = df_hits[df_hits['client_id_norm'].notna()]
            df_hits['ym:pv:clientID'] = df_hits['client_id_norm']
            if 'ym:pv:counterUserIDHash' in df_hits.columns:
                df_hits['counter_user_hash'] = df_hits['ym:pv:counterUserIDHash'].apply(normalize_client_id)
            else:
                df_hits['counter_user_hash'] = None
            self.stdout.write(f"DEBUG: Hits loaded. Shape: {df_hits.shape}")

            # 3. Process Visits (Sessions)
            self.stdout.write("Processing Visits...")

            sample_limit = int(os.environ.get("INGEST_SAMPLE_LIMIT", "10000"))
            if sample_limit > 0 and len(df_visits) > sample_limit:
                self.stdout.write(f"Sampling {sample_limit} visits from {len(df_visits)}...")
                df_visits = df_visits.head(sample_limit)
                client_ids = set(df_visits['client_id_norm'].unique())
                counter_hashes = set(df_visits['counter_user_hash'].dropna().unique()) if 'counter_user_hash' in df_visits else set()
                before_hits = len(df_hits)
                df_hits = df_hits[
                    df_hits['client_id_norm'].isin(client_ids)
                    | df_hits['counter_user_hash'].isin(counter_hashes)
                ]
                after_hits = len(df_hits)
                if after_hits == 0 and before_hits > 0:
                    self.stdout.write(self.style.WARNING(
                        "Filtered hits to 0 after sampling clients; keeping all hits to avoid data loss."
                    ))
                    df_hits = pd.read_parquet(hits_path, columns=hits_columns)
                    df_hits['ym:pv:dateTime'] = pd.to_datetime(df_hits['ym:pv:dateTime'], utc=True, errors='coerce')
                    df_hits['client_id_norm'] = df_hits['ym:pv:clientID'].apply(normalize_client_id)
                    df_hits = df_hits[df_hits['client_id_norm'].notna()]
                    df_hits['ym:pv:clientID'] = df_hits['client_id_norm']
                    if 'ym:pv:counterUserIDHash' in df_hits.columns:
                        df_hits['counter_user_hash'] = df_hits['ym:pv:counterUserIDHash'].apply(normalize_client_id)
                    else:
                        df_hits['counter_user_hash'] = None

            # Cache previous issues for routing comparisons
            self.prev_issue_index = self.build_previous_issue_index(version)

            # Bulk Create Sessions (оптимизировано: создаем и сохраняем батчами)
            self.stdout.write("Creating and saving visits in batches...")
            batch_size = 10000
            total_visits = len(df_visits)
            visit_map_by_client = {}
            counter_hash_to_client = {}
            
            for batch_start in range(0, total_visits, batch_size):
                batch_end = min(batch_start + batch_size, total_visits)
                batch_df = df_visits.iloc[batch_start:batch_end]
                
                visit_objects = []
                for _, row in batch_df.iterrows():
                    v_id = str(row.get('ym:s:visitID', ''))
                    c_id = str(row.get('client_id_norm', ''))
                    
                    # Обработка новых полей с проверкой на наличие
                    browser_val = row.get('ym:s:browser') if 'ym:s:browser' in row.index else None
                    os_val = row.get('ym:s:operatingSystem') if 'ym:s:operatingSystem' in row.index else None
                    screen_w = int(row.get('ym:s:screenWidth', 0)) if 'ym:s:screenWidth' in row.index and pd.notna(row.get('ym:s:screenWidth')) else None
                    screen_h = int(row.get('ym:s:screenHeight', 0)) if 'ym:s:screenHeight' in row.index and pd.notna(row.get('ym:s:screenHeight')) else None
                    screen_fmt = row.get('ym:s:screenFormat') if 'ym:s:screenFormat' in row.index else None
                    is_new = row.get('ym:s:isNewUser') if 'ym:s:isNewUser' in row.index else True
                    start_url = row.get('ym:s:startURL') if 'ym:s:startURL' in row.index else None
                    end_url = row.get('ym:s:endURL') if 'ym:s:endURL' in row.index else None
                    traffic_src = row.get('ym:s:lastsignReferalSource') if 'ym:s:lastsignReferalSource' in row.index else None
                    net_type = row.get('ym:s:networkType') if 'ym:s:networkType' in row.index else None
                    
                    # Обработка goalsID для воронок
                    goals_id_list = []
                    if 'ym:s:goalsID' in row.index:
                        goals_id_raw = row.get('ym:s:goalsID')
                        if pd.notna(goals_id_raw) and goals_id_raw:
                            # goalsID может быть списком, строкой списка, или числом
                            try:
                                if isinstance(goals_id_raw, (list, tuple)):
                                    goals_id_list = [int(g) for g in goals_id_raw if g]
                                elif isinstance(goals_id_raw, str):
                                    # Попытка распарсить строку "[12345, 67890]"
                                    import ast
                                    parsed = ast.literal_eval(goals_id_raw)
                                    if isinstance(parsed, list):
                                        goals_id_list = [int(g) for g in parsed if g]
                                    else:
                                        goals_id_list = [int(parsed)]
                                else:
                                    goals_id_list = [int(goals_id_raw)]
                            except (ValueError, SyntaxError, TypeError):
                                # Если не удалось распарсить, пропускаем
                                goals_id_list = []
                    
                    visit = VisitSession(
                        version=version,
                        visit_id=v_id,
                        client_id=c_id,
                        start_time=pd.to_datetime(row.get('ym:s:dateTime')),
                        duration_sec=int(row.get('ym:s:visitDuration', 0)),
                        device_category=row.get('ym:s:deviceCategory', 'unknown'),
                        source=row.get('ym:s:referer', ''),
                        bounced=bool(row.get('ym:s:bounce', 0)),
                        page_views=int(row.get('ym:s:pageViews', 0)),
                        # Новые поля
                        browser=browser_val if browser_val and pd.notna(browser_val) else None,
                        os=os_val if os_val and pd.notna(os_val) else None,
                        screen_width=screen_w if screen_w and screen_w > 0 else None,
                        screen_height=screen_h if screen_h and screen_h > 0 else None,
                        screen_format=screen_fmt if screen_fmt and pd.notna(screen_fmt) else None,
                        is_returning_visitor=not bool(is_new) if pd.notna(is_new) else False,
                        entry_page=start_url if start_url and pd.notna(start_url) else None,
                        exit_page=end_url if end_url and pd.notna(end_url) else None,
                        traffic_source=traffic_src if traffic_src and pd.notna(traffic_src) else None,
                        network_type=net_type if net_type and pd.notna(net_type) else None,
                        goals_id=goals_id_list if goals_id_list else [],
                    )
                    visit_objects.append(visit)
                    counter_hash = row.get('counter_user_hash') if 'counter_user_hash' in row else None
                    if pd.notna(counter_hash):
                        counter_hash_to_client[counter_hash] = c_id
                
                # Сохраняем батч и сразу получаем ID для маппинга
                created = VisitSession.objects.bulk_create(visit_objects, ignore_conflicts=True)
                # Получаем сохраненные объекты для маппинга
                for visit in visit_objects:
                    visit_map_by_client[visit.client_id] = visit
                
                if (batch_start // batch_size) % 10 == 0:
                    self.stdout.write(f"  Saved {batch_end}/{total_visits} visits...")
            
            self.stdout.write(f"Created {total_visits} sessions.")

            # Получаем маппинг client_id -> session_id из БД
            self.stdout.write("Loading visit mappings...")
            db_visits = VisitSession.objects.filter(version=version).values('id', 'client_id')
            client_to_visit_pk = {v['client_id']: v['id'] for v in db_visits}
            hash_to_visit_pk = {h: client_to_visit_pk[c] for h, c in counter_hash_to_client.items() if c in client_to_visit_pk}
            self.stdout.write(f"Loaded {len(client_to_visit_pk)} visit mappings.")

            # 4. Process Hits (оптимизировано: батчами)
            self.stdout.write("Processing and saving hits in batches...")
            hit_batch_size = 50000
            total_hits = len(df_hits)
            total_saved = 0
            
            for batch_start in range(0, total_hits, hit_batch_size):
                batch_end = min(batch_start + hit_batch_size, total_hits)
                batch_df = df_hits.iloc[batch_start:batch_end]
                
                hit_objects = []
                for _, row in batch_df.iterrows():
                    c_id = str(row.get('client_id_norm', ''))
                    counter_hash = row.get('counter_user_hash') if 'counter_user_hash' in row else None
                    session_id = None
                    if pd.notna(counter_hash) and counter_hash in hash_to_visit_pk:
                        session_id = hash_to_visit_pk[counter_hash]
                    elif c_id in client_to_visit_pk:
                        session_id = client_to_visit_pk[c_id]
                    if session_id:
                        # Обработка новых полей с проверкой на наличие
                        referrer = row.get('ym:pv:referer') if 'ym:pv:referer' in row.index else None
                        browser_val = row.get('ym:pv:browser') if 'ym:pv:browser' in row.index else None
                        os_val = row.get('ym:pv:operatingSystem') if 'ym:pv:operatingSystem' in row.index else None
                        screen_w = int(row.get('ym:pv:screenWidth', 0)) if 'ym:pv:screenWidth' in row.index and pd.notna(row.get('ym:pv:screenWidth')) else None
                        screen_h = int(row.get('ym:pv:screenHeight', 0)) if 'ym:pv:screenHeight' in row.index and pd.notna(row.get('ym:pv:screenHeight')) else None
                        device_cat = row.get('ym:pv:deviceCategory') if 'ym:pv:deviceCategory' in row.index else None
                        
                        hit = PageHit(
                            session_id=session_id,
                            timestamp=pd.to_datetime(row.get('ym:pv:dateTime')),
                            url=row.get('ym:pv:URL', ''),
                            page_title=row.get('ym:pv:title') if pd.notna(row.get('ym:pv:title', '')) else None,
                            action_type='view',
                            # Новые поля
                            referrer_url=referrer if referrer and pd.notna(referrer) else None,
                            browser=browser_val if browser_val and pd.notna(browser_val) else None,
                            os=os_val if os_val and pd.notna(os_val) else None,
                            screen_width=screen_w if screen_w and screen_w > 0 else None,
                            screen_height=screen_h if screen_h and screen_h > 0 else None,
                            device_category=device_cat if device_cat and pd.notna(device_cat) else None,
                            # time_on_page и is_exit будут рассчитаны позже
                        )
                        hit_objects.append(hit)
                
                # Сохраняем батч
                if hit_objects:
                    PageHit.objects.bulk_create(hit_objects, batch_size=5000)
                    total_saved += len(hit_objects)
                
                if (batch_start // hit_batch_size) % 5 == 0:
                    self.stdout.write(f"  Saved {total_saved} hits ({batch_end}/{total_hits} processed)...")
            
            self.stdout.write(f"Created {total_saved} hits.")
            
            # 4.5 Calculate time_on_page and is_exit
            self.calculate_time_on_page(version)
            
            # 4.6 Calculate page metrics
            self.calculate_page_metrics(version)

            # 5. Run Analysis (Heuristics)
            self.run_analysis(version, df_hits, df_visits)
            self.update_issue_lifecycle(version)

            # 6. Segment Users into Cohorts (New Logic)
            self.segment_users_into_cohorts(version, df_visits, df_hits, goals_config)
            
            # 6.5 Update dominant_cohort in PageMetrics after cohorts are created
            self.update_page_metrics_cohorts(version)

            # 7. Pre-calculate Daily Stats
            self.calculate_daily_stats(version)

            self.stdout.write(self.style.SUCCESS(f"Ingestion and analysis complete for {version_name}"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CRITICAL ERROR: {e}"))
            traceback.print_exc()

    def calculate_time_on_page(self, version):
        """Рассчитывает time_on_page для каждого hit и помечает is_exit (оптимизированная версия через SQL)"""
        self.stdout.write("Calculating time_on_page and exit flags...")
        from analytics.models import PageHit
        from django.db import connection
        
        # Используем SQL для быстрого расчета time_on_page (в 10-100 раз быстрее Python-цикла)
        with connection.cursor() as cursor:
            # Обновляем time_on_page через SQL window function
            cursor.execute("""
                UPDATE analytics_pagehit ph1
                SET time_on_page = GREATEST(0, EXTRACT(EPOCH FROM (
                    SELECT ph2.timestamp 
                    FROM analytics_pagehit ph2 
                    WHERE ph2.session_id = ph1.session_id 
                      AND ph2.timestamp > ph1.timestamp 
                    ORDER BY ph2.timestamp ASC 
                    LIMIT 1
                ) - ph1.timestamp))::INTEGER
                FROM analytics_visitsession vs
                WHERE ph1.session_id = vs.id 
                  AND vs.version_id = %s
                  AND ph1.time_on_page IS NULL
            """, [version.id])
            
            # Помечаем последние hits как exit
            cursor.execute("""
                UPDATE analytics_pagehit ph1
                SET is_exit = TRUE
                FROM analytics_visitsession vs
                WHERE ph1.session_id = vs.id 
                  AND vs.version_id = %s
                  AND ph1.id = (
                      SELECT ph2.id 
                      FROM analytics_pagehit ph2 
                      WHERE ph2.session_id = ph1.session_id 
                      ORDER BY ph2.timestamp DESC 
                      LIMIT 1
                  )
            """, [version.id])
        
        self.stdout.write("Updated time_on_page and exit flags via SQL (optimized).")

    def calculate_page_metrics(self, version):
        """Создает/обновляет PageMetrics для каждой страницы (оптимизированная версия)"""
        self.stdout.write("Calculating page metrics...")
        from analytics.models import PageMetrics, PageHit, VisitSession
        from django.db.models import Avg, Count, Q, Max
        from collections import defaultdict
        
        # Один запрос для всех метрик по страницам
        page_stats = PageHit.objects.filter(session__version=version).values('url').annotate(
            total_views=Count('id'),
            unique_visitors=Count('session__client_id', distinct=True),
            avg_time=Avg('time_on_page'),
            exit_count=Count('id', filter=Q(is_exit=True)),
            avg_scroll=Avg('scroll_depth'),
        )
        
        # Получаем dominant device и page_title одним запросом для всех страниц
        # Группируем по URL и берем самый частый device/title
        device_data = defaultdict(lambda: defaultdict(int))
        title_data = defaultdict(lambda: defaultdict(int))
        
        # Batch-обработка для device и title
        hits_for_stats = PageHit.objects.filter(
            session__version=version
        ).values('url', 'device_category', 'page_title').exclude(
            device_category__isnull=True
        )
        
        for hit in hits_for_stats:
            url = hit['url']
            if hit['device_category']:
                device_data[url][hit['device_category']] += 1
            if hit['page_title']:
                title_data[url][hit['page_title']] += 1
        
        # Создаем/обновляем PageMetrics батчами
        metrics_to_create = []
        for stat in page_stats:
            url = stat['url']
            total_views = stat['total_views']
            exit_rate = (stat['exit_count'] / total_views * 100) if total_views else 0
            
            # Берем самый частый device и title из предварительно собранных данных
            dominant_device = max(device_data[url].items(), key=lambda x: x[1])[0] if device_data[url] else None
            page_title = max(title_data[url].items(), key=lambda x: x[1])[0] if title_data[url] else None
            
            metrics_to_create.append(PageMetrics(
                version=version,
                url=url,
                page_title=page_title,
                total_views=total_views,
                unique_visitors=stat['unique_visitors'],
                avg_time_on_page=stat['avg_time'] or 0,
                bounce_rate=0,
                exit_rate=exit_rate,
                avg_scroll_depth=stat['avg_scroll'],
                dominant_device=dominant_device,
                dominant_cohort=None,
            ))
        
        # Bulk create/update (используем update_or_create для совместимости)
        for metric in metrics_to_create:
            PageMetrics.objects.update_or_create(
                version=metric.version,
                url=metric.url,
                defaults={
                    'page_title': metric.page_title,
                    'total_views': metric.total_views,
                    'unique_visitors': metric.unique_visitors,
                    'avg_time_on_page': metric.avg_time_on_page,
                    'bounce_rate': metric.bounce_rate,
                    'exit_rate': metric.exit_rate,
                    'avg_scroll_depth': metric.avg_scroll_depth,
                    'dominant_device': metric.dominant_device,
                }
            )
        
        self.stdout.write(f"Calculated metrics for {len(page_stats)} pages.")

    def update_page_metrics_cohorts(self, version):
        """Обновляет dominant_cohort в PageMetrics после создания когорт (оптимизированная версия)"""
        from analytics.models import PageMetrics, UserCohort
        
        # Берем самую большую когорту как приближение для всех страниц
        # (более точное определение требует сложной логики связывания client_id)
        cohorts = UserCohort.objects.filter(version=version).order_by('-percentage')
        
        if cohorts.exists():
            dominant_cohort = cohorts.first().name
            # Bulk update всех страниц сразу
            PageMetrics.objects.filter(version=version).update(dominant_cohort=dominant_cohort)
            self.stdout.write(f"Updated dominant_cohort for all pages (using '{dominant_cohort}').")
        else:
            self.stdout.write("No cohorts found, skipping dominant_cohort update.")

    def run_analysis(self, version, df_hits, df_visits):
        """Запускает анализ UX-проблем с AI-гипотезами"""
        self.stdout.write("Running UX Analysis...")
        issues = []

        def normalize_issue_url(raw_url):
            """
            Collapse noisy params (referer/utm/etc) and trailing slashes so the same page
            does not create multiple issues due to query strings or mixed schemes.
            """
            if not isinstance(raw_url, str):
                return ""
            parsed = urllib.parse.urlparse(raw_url.strip())
            netloc = parsed.netloc.lower()
            path = (parsed.path or "/").rstrip("/") or "/"
            query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
            for noisy in ['referer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'yclid', '_openstat', 'from', 'ref']:
                query_dict.pop(noisy, None)
            clean_query = urllib.parse.urlencode({k: v[0] if len(v) == 1 else v for k, v in query_dict.items()}, doseq=True)
            scheme = parsed.scheme.lower() if parsed.scheme else ("https" if netloc else "")
            if netloc or scheme:
                return urllib.parse.urlunparse((scheme, netloc, path, '', clean_query, ''))
            return path + (f"?{clean_query}" if clean_query else "")

        def pick_representative_url(df, norm_column, norm_value):
            """Return the most frequent raw URL for a normalized value to fetch PageMetrics."""
            subset = df[df[norm_column] == norm_value]['ym:pv:URL'].dropna()
            if subset.empty:
                return norm_value
            return subset.mode().iloc[0]

        # A. Rage Clicks Detection
        df_hits['timestamp'] = pd.to_datetime(df_hits['ym:pv:dateTime'], utc=True)
        df_hits_sorted = df_hits.sort_values(['ym:pv:clientID', 'timestamp'])
        df_hits_sorted['time_diff'] = df_hits_sorted.groupby('ym:pv:clientID')['timestamp'].diff().dt.total_seconds()
        df_hits_sorted['prev_url'] = df_hits_sorted.groupby('ym:pv:clientID')['ym:pv:URL'].shift()
        
        rage_clicks = df_hits_sorted[
            (df_hits_sorted['time_diff'] < 2) & 
            (df_hits_sorted['ym:pv:URL'] == df_hits_sorted['prev_url'])
        ].copy()
        
        if not rage_clicks.empty:
            rage_clicks['norm_url'] = rage_clicks['ym:pv:URL'].apply(normalize_issue_url)
            rage_stats = rage_clicks['norm_url'].value_counts().head(5)
            for norm_url, count in rage_stats.items():
                if not norm_url:
                    continue
                representative_url = pick_representative_url(rage_clicks, 'norm_url', norm_url)
                page_metrics = PageMetrics.objects.filter(version=version, url=representative_url).first()
                if not page_metrics:
                    page_metrics = PageMetrics.objects.filter(version=version, url=norm_url).first()
                impact = min(count * 0.1, 10.0)
                trend = self._calculate_trend('RAGE_CLICK', norm_url, impact)
                priority = self._calculate_priority('WARNING', impact, count, trend)
                ai_text = analyze_issue_with_ai(
                     issue_type='RAGE_CLICK',
                     location=norm_url,
                     metrics_context=f"Количество событий: {count}",
                     page_title=page_metrics.page_title if page_metrics else None,
                     page_metrics={'avg_time': page_metrics.avg_time_on_page if page_metrics else None} if page_metrics else None,
                     dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                     dominant_device=page_metrics.dominant_device if page_metrics else None
                 )
                issues.append(UXIssue(
                    version=version,
                    issue_type='RAGE_CLICK',
                    severity='WARNING',
                description=f"Обнаружены {count} быстрых повторных кликов/перезагрузок на странице.",
                    location_url=norm_url,
                    affected_sessions=count,
                    impact_score=impact,
                    ai_hypothesis=ai_text,
                    detected_version_name=version.name,
                    trend=trend,
                    priority=priority,
                    recommended_specialists=self._recommend_specialists('RAGE_CLICK')
                ))

        nav_back_targets = set()

        # B. Loops
        df_hits['norm_url'] = df_hits['ym:pv:URL'].apply(normalize_issue_url)
        loop_counts = df_hits[df_hits['norm_url'] != ""].groupby(['ym:pv:clientID', 'norm_url']).size()
        loops = loop_counts[loop_counts > 3]
        
        if not loops.empty:
            loop_urls = loops.index.get_level_values('norm_url').value_counts().head(5)
            for norm_url, count in loop_urls.items():
                if not norm_url:
                    continue
                nav_back_targets.add(norm_url)
                page_metrics = PageMetrics.objects.filter(version=version, url=norm_url).first()
                impact = min(count * 0.15, 10.0)
                trend = self._calculate_trend('LOOPING', norm_url, impact)
                priority = self._calculate_priority('WARNING', impact, count, trend)
                ai_text = analyze_issue_with_ai(
                     issue_type='LOOPING',
                     location=norm_url,
                     metrics_context=f"Количество зацикливаний: {count}",
                     page_title=page_metrics.page_title if page_metrics else None,
                     page_metrics={'avg_time': page_metrics.avg_time_on_page if page_metrics else None} if page_metrics else None,
                     dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                     dominant_device=page_metrics.dominant_device if page_metrics else None
                 )
                issues.append(UXIssue(
                    version=version,
                    issue_type='LOOPING',
                    severity='WARNING',
                    description=f"Пользователи возвращаются на эту страницу (циклов: {count}).",
                    location_url=norm_url,
                    affected_sessions=count,
                    impact_score=impact,
                    ai_hypothesis=ai_text,
                    detected_version_name=version.name,
                    trend=trend,
                    priority=priority,
                    recommended_specialists=self._recommend_specialists('LOOPING')
                ))

        # C. WANDERING (Блуждание) - сессии с >10 просмотрами, но без целей
        if 'ym:s:goalsID' in df_visits.columns:
            wandering_visits = df_visits[
                (df_visits['ym:s:pageViews'] > 10) & 
                (df_visits['ym:s:goalsID'].isna() | (df_visits['ym:s:goalsID'].astype(str) == '[]'))
            ].copy()
            
            if not wandering_visits.empty:
                wandering_visits['norm_start_url'] = wandering_visits['ym:s:startURL'].apply(normalize_issue_url)
                wandering_by_page = wandering_visits.groupby('norm_start_url').size()
                for entry_page, count in wandering_by_page.head(5).items():
                    if not entry_page:
                        continue
                    # Отсеиваем шум: слишком мало сессий
                    if count < MIN_WANDERING_SESSIONS:
                        continue
                    # Получаем метрики страницы
                    page_metrics = PageMetrics.objects.filter(version=version, url=entry_page).first()
                    avg_depth = wandering_visits[wandering_visits['norm_start_url'] == entry_page]['ym:s:pageViews'].mean()
                    metrics_context = f"Количество сессий: {count}, Средняя глубина: {avg_depth:.1f}"
                    
                    ai_text = analyze_issue_with_ai(
                        issue_type='WANDERING',
                        location=entry_page,
                        metrics_context=metrics_context,
                        page_title=page_metrics.page_title if page_metrics else None,
                        page_metrics={'avg_time': page_metrics.avg_time_on_page if page_metrics else None,
                                     'exit_rate': page_metrics.exit_rate if page_metrics else None} if page_metrics else None,
                        dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                        dominant_device=page_metrics.dominant_device if page_metrics else None
                    )
                    issues.append(UXIssue(
                        version=version,
                        issue_type='WANDERING',
                        severity='WARNING',
                        description=f"Пользователи блуждают по {avg_depth:.1f} страницам без достижения целей.",
                        location_url=entry_page,
                        affected_sessions=count,
                        impact_score=min(count * 0.1, 10.0),
                        ai_hypothesis=ai_text
                    ))

        # D. NAVIGATION_BACK (Частое использование "Назад")
        df_hits_sorted = df_hits.sort_values(['ym:pv:clientID', 'ym:pv:dateTime'])
        if not df_hits_sorted.empty:
            def canonical_loop_key(path_tuple):
                """
                Сводит петли к канонической форме, чтобы A->B->A и B->A->B считались одним паттерном.
                Для двувершинных циклов сортируем вершины; для остальных оставляем как есть.
                """
                unique_nodes = set(path_tuple)
                if len(unique_nodes) == 2:
                    return tuple(sorted(unique_nodes))
                return path_tuple

            def canonical_loop_display(path_tuple):
                """Возвращает детерминированное отображение для канонического ключа."""
                unique_nodes = set(path_tuple)
                if len(unique_nodes) == 2:
                    a, b = sorted(unique_nodes)
                    return f"{a} -> {b} -> {a}"
                return " -> ".join(path_tuple)

            # Собираем навигационные циклы 2-3 страниц, чтобы не плодить дубликаты issues
            loop_events = []
            for client_id, group in df_hits_sorted.groupby('ym:pv:clientID'):
                urls = group['ym:pv:URL'].tolist()
                for idx in range(len(urls)):
                    for window in (2, 3):  # A->B->A and A->B->C->A
                        if idx >= window:
                            seq = urls[idx-window:idx+1]
                            norm_seq = [normalize_issue_url(u) for u in seq]
                            if norm_seq[0] and norm_seq[-1] and norm_seq[0] == norm_seq[-1] and len(set(norm_seq)) > 1:
                                key = canonical_loop_key(tuple(norm_seq))
                                display = canonical_loop_display(tuple(norm_seq))
                                loop_events.append((key, display, client_id))

            if loop_events:
                from collections import defaultdict
                path_counts = defaultdict(int)
                path_users = defaultdict(set)
                path_display = {}
                for path_key, display_path, client_id in loop_events:
                    path_counts[path_key] += 1
                    path_users[path_key].add(client_id)
                    if path_key not in path_display:
                        path_display[path_key] = display_path

                top_loops = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for path_key, pattern_count in top_loops:
                    loop_path = path_display.get(path_key, " -> ".join(path_key))
                    users_count = len(path_users[path_key])
                    # Берем вторую страницу как проблемную точку для метрик, если есть
                    target_url = path_key[1] if len(path_key) > 1 else path_key[0]
                    nav_back_targets.add(target_url)
                    page_metrics = PageMetrics.objects.filter(version=version, url=target_url).first()
                    metrics_context = f"Навигационный цикл: {loop_path}. Повторений: {pattern_count}, пользователей: {users_count}"
                    impact = min(pattern_count * 0.12, 10.0)
                    trend = self._calculate_trend('NAVIGATION_BACK', loop_path, impact)
                    priority = self._calculate_priority('WARNING', impact, users_count, trend)

                    ai_text = analyze_issue_with_ai(
                        issue_type='NAVIGATION_BACK',
                        location=loop_path,
                        metrics_context=metrics_context,
                        page_title=page_metrics.page_title if page_metrics else None,
                        page_metrics={'avg_time': page_metrics.avg_time_on_page if page_metrics else None} if page_metrics else None,
                        dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                        dominant_device=page_metrics.dominant_device if page_metrics else None
                    )
                    issues.append(UXIssue(
                        version=version,
                        issue_type='NAVIGATION_BACK',
                        severity='WARNING',
                        description=f"Пользователи ходят по петле {loop_path} ({pattern_count} паттернов, {users_count} пользователей).",
                        location_url=loop_path,
                        affected_sessions=users_count,
                        impact_score=impact,
                        ai_hypothesis=ai_text,
                        detected_version_name=version.name,
                        trend=trend,
                        priority=priority,
                        recommended_specialists=self._recommend_specialists('LOOPING')
                    ))

        # E. HIGH_BOUNCE после учета back-циклов: если страница уже в back loop, не плодим дубль
        bounced_visits = df_visits[df_visits['ym:s:visitDuration'] < 15]['ym:s:clientID']
        bounced_hits = df_hits[df_hits['ym:pv:clientID'].isin(bounced_visits)].copy()
        
        if not bounced_hits.empty:
            bounced_hits['norm_url'] = bounced_hits['ym:pv:URL'].apply(normalize_issue_url)
            bounce_stats = bounced_hits['norm_url'].value_counts().head(5)
            for norm_url, count in bounce_stats.items():
                 if not norm_url:
                     continue
                 if norm_url in nav_back_targets:
                     continue  # уже покрыто back-loop проблемой
                 representative_url = pick_representative_url(bounced_hits, 'norm_url', norm_url)
                 page_metrics = PageMetrics.objects.filter(version=version, url=representative_url).first()
                 if not page_metrics:
                     page_metrics = PageMetrics.objects.filter(version=version, url=norm_url).first()
                 impact = min(count * 0.2, 10.0)
                 trend = self._calculate_trend('HIGH_BOUNCE', norm_url, impact)
                 priority = self._calculate_priority('CRITICAL', impact, count, trend)
                 ai_text = analyze_issue_with_ai(
                     issue_type='HIGH_BOUNCE',
                     location=norm_url,
                     metrics_context=f"Количество отказов: {count}",
                     page_title=page_metrics.page_title if page_metrics else None,
                     page_metrics={'exit_rate': page_metrics.exit_rate if page_metrics else None,
                                  'avg_time': page_metrics.avg_time_on_page if page_metrics else None} if page_metrics else None,
                     dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                     dominant_device=page_metrics.dominant_device if page_metrics else None
                 )
                 issues.append(UXIssue(
                    version=version,
                    issue_type='HIGH_BOUNCE',
                    severity='CRITICAL',
                    description=f"Высокий отскок: {count} пользователей ушли сразу.",
                    location_url=norm_url,
                    affected_sessions=count,
                    impact_score=impact,
                    ai_hypothesis=ai_text,
                    detected_version_name=version.name,
                    trend=trend,
                    priority=priority,
                    recommended_specialists=self._recommend_specialists('HIGH_BOUNCE')
                ))

        # F. FORM_FIELD_ERRORS (Ошибки ввода в формах)
        form_pattern = r'/form|/apply|/request|/anket|/zayav'
        form_hits = df_hits[df_hits['ym:pv:URL'].astype(str).str.contains(form_pattern, na=False, regex=True)]
        
        if not form_hits.empty:
            # Нормализуем время и режем на «квазисессии» с разрывом >30 минут, чтобы не суммировать дни
            form_hits = form_hits.copy()
            form_hits['ym:pv:dateTime'] = pd.to_datetime(form_hits['ym:pv:dateTime'], utc=True, errors='coerce')
            form_hits = form_hits.dropna(subset=['ym:pv:dateTime'])
            form_hits = form_hits.sort_values(['ym:pv:clientID', 'ym:pv:dateTime'])
            form_hits['time_diff'] = form_hits.groupby('ym:pv:clientID')['ym:pv:dateTime'].diff().dt.total_seconds().fillna(0)
            form_hits['session_group'] = form_hits.groupby('ym:pv:clientID')['time_diff'].transform(lambda x: (x > 1800).cumsum())
            form_hits['session_key'] = form_hits['ym:pv:clientID'].astype(str) + "_" + form_hits['session_group'].astype(str)

            form_sessions = form_hits.groupby('session_key').agg(
                client_id=('ym:pv:clientID', 'first'),
                url=('ym:pv:URL', 'first'),
                min_time=('ym:pv:dateTime', 'min'),
                max_time=('ym:pv:dateTime', 'max'),
            )
            form_sessions['duration'] = (form_sessions['max_time'] - form_sessions['min_time']).dt.total_seconds()
            # Отсекаем явно сломанные длительности (>2 часов)
            form_sessions = form_sessions[form_sessions['duration'] <= 7200]
            
            # Долго на форме (>60 сек) и нет цели
            long_form = form_sessions[form_sessions['duration'] > 60]
            if not long_form.empty:
                long_form_clients = long_form['client_id']
                # Проверяем, есть ли у этих пользователей goals
                if 'ym:s:goalsID' in df_visits.columns:
                    has_goals = df_visits[
                        df_visits['ym:s:clientID'].isin(long_form_clients) & 
                        ~df_visits['ym:s:goalsID'].isna() &
                        (df_visits['ym:s:goalsID'].astype(str) != '[]')
                    ]
                    problem_clients = set(long_form_clients) - set(has_goals['ym:s:clientID'])
                else:
                    problem_clients = set(long_form_clients)
                
                if problem_clients:
                    form_urls = long_form[long_form['client_id'].isin(problem_clients)]['url'].value_counts().head(5)
                    for url, count in form_urls.items():
                        norm_url = normalize_issue_url(url)
                        page_metrics = PageMetrics.objects.filter(version=version, url=norm_url or url).first()
                        avg_duration = long_form[long_form['url'] == url]['duration'].mean()
                        metrics_context = f"Количество проблемных сессий: {count}, Среднее время на форме: {avg_duration:.1f} сек"
                        
                        ai_text = analyze_issue_with_ai(
                            issue_type='FORM_FIELD_ERRORS',
                            location=norm_url or url,
                            metrics_context=metrics_context,
                            page_title=page_metrics.page_title if page_metrics else None,
                            page_metrics={'avg_time': avg_duration} if page_metrics else None,
                            dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                            dominant_device=page_metrics.dominant_device if page_metrics else None
                        )
                        issues.append(UXIssue(
                            version=version,
                            issue_type='FORM_FIELD_ERRORS',
                            severity='WARNING',
                            description=f"Пользователи проводят {avg_duration:.1f} с на форме и не отправляют (сессий: {count}).",
                            location_url=norm_url or url,
                            affected_sessions=count,
                            impact_score=min(count * 0.15, 10.0),
                            ai_hypothesis=ai_text
                        ))

        # G. FUNNEL_DROPOFF (Критические точки отказа в воронках)
        # Для приемной комиссии/банка: определяем популярные пути
        funnel_steps = ['/', '/lists', '/rating', '/apply']
        
        for i in range(len(funnel_steps) - 1):
            step1_url = normalize_issue_url(funnel_steps[i])
            step2_url = normalize_issue_url(funnel_steps[i+1])
            
            step1_users = set(df_hits[df_hits['norm_url'] == step1_url]['ym:pv:clientID'])
            step2_users = set(df_hits[df_hits['norm_url'] == step2_url]['ym:pv:clientID'])
            
            # Порог по количеству, чтобы не создавать шумные дропы
            if step1_users and len(step1_users) >= 50:
                conversion = len(step2_users & step1_users) / len(step1_users)
                
                if conversion < 0.3:  # <30% конверсия = критическая точка
                    lost_users = len(step1_users) - len(step2_users & step1_users)
                    page_metrics = PageMetrics.objects.filter(version=version, url=step1_url).first() or PageMetrics.objects.filter(version=version, url=funnel_steps[i]).first()
                    metrics_context = f"Конверсия {step1_url} -> {step2_url}: {conversion*100:.1f}%, Потеряно пользователей: {lost_users}"
                    
                    ai_text = analyze_issue_with_ai(
                        issue_type='FUNNEL_DROPOFF',
                        location=step1_url,
                        metrics_context=metrics_context,
                        page_title=page_metrics.page_title if page_metrics else None,
                        page_metrics={'exit_rate': page_metrics.exit_rate if page_metrics else None} if page_metrics else None,
                        dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                        dominant_device=page_metrics.dominant_device if page_metrics else None
                    )
                    issues.append(UXIssue(
                        version=version,
                        issue_type='FUNNEL_DROPOFF',
                        severity='CRITICAL',
                        description=f"Критический отвал: только {conversion*100:.1f}% переходят с {step1_url} на {step2_url}.",
                        location_url=step1_url,
                        affected_sessions=lost_users,
                        impact_score=min(lost_users * 0.2, 10.0),
                        ai_hypothesis=ai_text
                    ))

        # H. SCAN_AND_DROP: высокие выходы при глубоком скролле и коротком времени
        scan_drop_candidates = PageMetrics.objects.filter(
            version=version,
            avg_scroll_depth__gte=80,
            total_views__gte=MIN_PAGE_VIEWS_FOR_PAGE_ALERT
        ).order_by('-exit_rate')[:5]
        for metric in scan_drop_candidates:
            if metric.exit_rate and metric.exit_rate > 70 and metric.avg_time_on_page < 30:
                norm_url = normalize_issue_url(metric.url)
                impact = min(metric.exit_rate / 10, 10.0)
                ai_text = analyze_issue_with_ai(
                    issue_type='SCAN_AND_DROP',
                    location=norm_url,
                    metrics_context=f"Exit rate: {metric.exit_rate:.1f}%, Avg time: {metric.avg_time_on_page:.1f}s, Scroll: {metric.avg_scroll_depth:.1f}%",
                    page_title=metric.page_title,
                    page_metrics={
                        'exit_rate': metric.exit_rate,
                        'avg_time': metric.avg_time_on_page,
                        'scroll_depth': metric.avg_scroll_depth,
                    },
                    dominant_cohort=metric.dominant_cohort,
                    dominant_device=metric.dominant_device
                )
                issues.append(UXIssue(
                    version=version,
                    issue_type='SCAN_AND_DROP',
                    severity='WARNING',
                    description=f"Быстрый просмотр и уход (выход {metric.exit_rate:.1f}%, время {metric.avg_time_on_page:.1f} с).",
                    location_url=norm_url,
                    affected_sessions=int(metric.total_views),
                    impact_score=impact,
                    ai_hypothesis=ai_text
                ))

        # J. DEAD_CLICK: страницы с высоким выходом и почти нулевым вовлечением
        dead_candidates = PageMetrics.objects.filter(
            version=version,
            total_views__gte=MIN_PAGE_VIEWS_FOR_PAGE_ALERT,
            exit_rate__gte=60,
            avg_time_on_page__lte=5
        ).order_by('-exit_rate')[:5]
        for metric in dead_candidates:
            if metric.avg_scroll_depth is not None and metric.avg_scroll_depth > 20:
                continue  # не считаем, если есть скролл
            norm_url = normalize_issue_url(metric.url)
            impact = min(metric.exit_rate / 8, 10.0)
            ai_text = analyze_issue_with_ai(
                issue_type='DEAD_CLICK',
                location=norm_url,
                metrics_context=f"Exit rate: {metric.exit_rate:.1f}%, Avg time: {metric.avg_time_on_page:.1f}s, Scroll: {metric.avg_scroll_depth}",
                page_title=metric.page_title,
                page_metrics={
                    'exit_rate': metric.exit_rate,
                    'avg_time': metric.avg_time_on_page,
                    'scroll_depth': metric.avg_scroll_depth,
                },
                dominant_cohort=metric.dominant_cohort,
                dominant_device=metric.dominant_device
            )
            issues.append(UXIssue(
                version=version,
                issue_type='DEAD_CLICK',
                severity='WARNING',
                description=f"Похоже на мёртвые клики: выход {metric.exit_rate:.1f}%, время {metric.avg_time_on_page:.1f} с.",
                location_url=norm_url,
                affected_sessions=int(metric.total_views),
                impact_score=impact,
                ai_hypothesis=ai_text
            ))

        # I. SEARCH_FAIL: страницы поиска с высоким exit
        search_metrics = PageMetrics.objects.filter(
            version=version,
            url__icontains='search',
            total_views__gte=MIN_PAGE_VIEWS_FOR_PAGE_ALERT
        ).order_by('-exit_rate')[:5]
        for metric in search_metrics:
            if metric.exit_rate and metric.exit_rate > 70:
                norm_url = normalize_issue_url(metric.url)
                impact = min(metric.exit_rate / 8, 10.0)
                ai_text = analyze_issue_with_ai(
                    issue_type='SEARCH_FAIL',
                    location=norm_url,
                    metrics_context=f"Search exit rate: {metric.exit_rate:.1f}%, Avg time: {metric.avg_time_on_page:.1f}s",
                    page_title=metric.page_title,
                    page_metrics={
                        'exit_rate': metric.exit_rate,
                        'avg_time': metric.avg_time_on_page,
                    },
                    dominant_cohort=metric.dominant_cohort,
                    dominant_device=metric.dominant_device
                )
                issues.append(UXIssue(
                    version=version,
                    issue_type='SEARCH_FAIL',
                    severity='WARNING',
                    description=f"Страница поиска с высоким выходом ({metric.exit_rate:.1f}%).",
                    location_url=norm_url,
                    affected_sessions=int(metric.total_views),
                    impact_score=impact,
                    ai_hypothesis=ai_text
                ))

        UXIssue.objects.bulk_create(issues)
        self.stdout.write(f"Найдено {len(issues)} UX-проблем.")

    def build_previous_issue_index(self, version):
        """
        Собирает последнюю известную проблему на каждую пару (тип, URL) в более старых версиях.
        Используется для расчета динамики.
        """
        older_issues = UXIssue.objects.filter(
            version__release_date__lt=version.release_date
        ).order_by('-created_at')

        index = {}
        for issue in older_issues:
            key = (issue.issue_type, issue.location_url)
            if key not in index:
                index[key] = issue
        return index

    def _calculate_trend(self, issue_type, location_url, impact_score):
        """
        Возвращает строковый код динамики: new/worse/improved/stable.
        """
        if not hasattr(self, 'prev_issue_index'):
            return "new"

        previous = self.prev_issue_index.get((issue_type, location_url))
        if not previous:
            return "new"

        diff = impact_score - (previous.impact_score or 0)
        if diff > 1:
            return "worse"
        if diff < -1:
            return "improved"
        return "stable"

    def _calculate_priority(self, severity, impact_score, affected_sessions, trend):
        """
        Грубая приоритизация для роутинга задач.
        """
        base = "P2"
        if severity == 'CRITICAL' or impact_score >= 8 or affected_sessions >= 100:
            base = "P0"
        elif severity == 'WARNING' or impact_score >= 5 or affected_sessions >= 50:
            base = "P1"

        if trend == "worse" and base != "P0":
            return "P1" if base == "P2" else base
        return base

    def _recommend_specialists(self, issue_type):
        """
        Выбирает подходящих специалистов под тип проблемы.
        """
        mapping = {
            'RAGE_CLICK': ['UX-дизайнер', 'Фронтенд-разработчик'],
            'DEAD_CLICK': ['UX-дизайнер', 'Фронтенд-разработчик'],
            'LOOPING': ['UX-дизайнер', 'Аналитик'],
            'FORM_ABANDON': ['UX-дизайнер', 'Фронтенд-разработчик', 'Аналитик'],
            'HIGH_BOUNCE': ['UX-дизайнер', 'Аналитик'],
        }
        roles = mapping.get(issue_type, ['Аналитик'])
        return list(dict.fromkeys(roles))  # preserve order, drop duplicates

    def segment_users_into_cohorts(self, version, df_visits, df_hits, goals_config):
        self.stdout.write("--- Starting User Segmentation ---")

        # 1. Base User Metrics
        user_behavior = df_visits.groupby('ym:s:clientID').agg({
            'ym:s:visitDuration': 'mean',       # Avg duration
            'ym:s:pageViews': 'mean',           # Avg depth
            'ym:s:visitID': 'count',            # Total visits
            'ym:s:bounce': 'mean'               # Bounce prob
        }).rename(columns={
            'ym:s:visitDuration': 'avg_duration',
            'ym:s:pageViews': 'avg_depth',
            'ym:s:visitID': 'total_visits',
            'ym:s:bounce': 'bounce_prob'
        }).fillna(0)

        # 2. Calculate Goal Achievements per User
        # We add a column for each goal: 1 if achieved, 0 if not
        
        # Pre-process hits for URL matching
        # Group hits by client to quickly check URLs
        # This might be slow for huge datasets, but OK for hackathon size
        
        self.stdout.write("Calculating goal achievements...")
        
        # 2a. Identifier goals (ym:s:goalsID from Visits)
        if 'ym:s:goalsID' in df_visits.columns:
            # Expand goalsID list/string
            # Metrica often sends '[12345, 67890]' string
            def check_goal_id(row_val, target_id):
                return str(target_id) in str(row_val)

            for goal in goals_config:
                if goal['match']['type'] == 'identifier':
                    goal_id = goal['ym_goal_id']
                    col_name = f"goal_{goal['code']}"
                    # Check if any visit of this user has this goal ID
                    # We do this by aggregating: did the user EVER have this goal?
                    
                    # Helper series
                    has_goal = df_visits['ym:s:goalsID'].apply(lambda x: check_goal_id(x, goal_id)).astype(int)
                    user_goal_counts = df_visits.assign(temp_goal=has_goal).groupby('ym:s:clientID')['temp_goal'].max()
                    user_behavior[col_name] = user_goal_counts

        # 2b. URL/Click goals (from Hits)
        # Group hits by clientID
        hits_grouped = df_hits.groupby('ym:pv:clientID')
        
        for goal in goals_config:
            match_type = goal['match']['type']
            match_val = goal['match']['value']
            col_name = f"goal_{goal['code']}"
            
            if col_name in user_behavior.columns: 
                continue # Already processed (e.g. identifier)

            if match_type == 'url_contains':
                # Find clients who have at least one hit with url containing value
                matching_clients = df_hits[df_hits['ym:pv:URL'].astype(str).str.contains(match_val, na=False)]['ym:pv:clientID'].unique()
                user_behavior[col_name] = 0
                user_behavior.loc[user_behavior.index.isin(matching_clients), col_name] = 1
            
            elif match_type == 'url_prefix':
                 matching_clients = df_hits[df_hits['ym:pv:URL'].astype(str).str.startswith(match_val, na=False)]['ym:pv:clientID'].unique()
                 user_behavior[col_name] = 0
                 user_behavior.loc[user_behavior.index.isin(matching_clients), col_name] = 1
            
            # For 'click' or others we might skip if we don't have specific click events in hits, 
            # or assume they map to identifier if Metrica tracks them as JS goals.
            # We'll initialize with 0 if not handled.
            if col_name not in user_behavior.columns:
                user_behavior[col_name] = 0

        # Fill NaNs
        user_behavior = user_behavior.fillna(0)

        # 2c. Interest features from URLs (to split users by intent: списки/новости/контакты/поступление)
        self.stdout.write("Deriving interest intents from URLs...")
        url_df = df_hits[['ym:pv:clientID', 'ym:pv:URL']].copy()
        url_df['url_lower'] = url_df['ym:pv:URL'].astype(str).str.lower()

        interest_map = {
            'interest_rating': ['rating', 'spis', 'rank'],
            'interest_news': ['news', 'novosti', 'press'],
            'interest_contacts': ['contact', 'kontak'],
            'interest_admission': ['apply', 'priem', 'postup', 'admission'],
            'interest_forms': ['form', 'anket', 'request'],
            'interest_programs': ['program', 'napravlen', 'course'],
        }

        for col, keywords in interest_map.items():
            pattern = "|".join(keywords)
            matched_clients = url_df[url_df['url_lower'].str.contains(pattern, na=False)]['ym:pv:clientID'].unique()
            user_behavior[col] = 0
            if len(matched_clients):
                user_behavior.loc[user_behavior.index.isin(matched_clients), col] = 1

        # 3. Clustering (ML)
        if user_behavior.empty:
            self.stdout.write("Нет пользователей для сегментации.")
            return

        self.stdout.write("Running K-Means...")
        scaler = StandardScaler()
        # Select features: standard metrics + all goal columns
        feature_cols = ['avg_duration', 'avg_depth', 'total_visits', 'bounce_prob'] 
        # Add goal columns to clustering features? 
        # Ideally yes, so we separate "Buyers" from "Readers"
        goal_cols = [c for c in user_behavior.columns if c.startswith('goal_')]
        interest_cols = [c for c in user_behavior.columns if c.startswith('interest_')]
        feature_cols += goal_cols + interest_cols
        
        X = scaler.fit_transform(user_behavior[feature_cols])
        
        # More granular cohorts: choose up to 8 clusters, but never exceed user count
        # Aim for more segments: ~1 per 30 users, between 5 and 10 where possible
        n_clusters = min(10, max(5, len(user_behavior)//30 or 5))
        n_clusters = min(n_clusters, len(user_behavior))
        if n_clusters < 2:
            n_clusters = 1
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        user_behavior['cluster'] = kmeans.fit_predict(X)
        
        # 4. Save & Name Cohorts (AI)
        UserCohort.objects.filter(version=version).delete()
        combined = {}

        for cluster_id in range(n_clusters):
            cluster_data = user_behavior[user_behavior['cluster'] == cluster_id]
            
            # Calculate avg metrics
            avg_bounce = cluster_data['bounce_prob'].mean()
            avg_duration = cluster_data['avg_duration'].mean()
            avg_depth = cluster_data['avg_depth'].mean()
            
            # Calculate conversion rates for goals (mean of 0/1 flags)
            conversions = {}
            top_goals = []
            for gc in goal_cols:
                rate = cluster_data[gc].mean()
                if rate > 0:
                    conversions[gc.replace('goal_', '')] = round(rate, 4)
                    if rate > 0.05: # 5% threshold for "significant" goal
                        top_goals.append(f"{gc.replace('goal_', '')}({int(rate*100)}%)")

            # Interest breakdown (which URL intents dominate this cluster)
            interest_labels = {
                'rating': 'рейтинги',
                'news': 'новости',
                'contacts': 'контакты',
                'admission': 'поступление',
                'forms': 'формы',
                'programs': 'программы'
            }
            interest_rates = []
            for ic in interest_cols:
                rate = cluster_data[ic].mean()
                if rate > 0:
                    code = ic.replace('interest_', '')
                    interest_rates.append((code, rate))
            interest_rates.sort(key=lambda x: x[1], reverse=True)
            top_interest_codes = [c for c, _ in interest_rates[:3]]
            interest_summary = []
            for code, rate in interest_rates[:3]:
                label = interest_labels.get(code, code)
                interest_summary.append(f"{label} ({int(rate*100)}%)")
            top_interests = ", ".join(interest_summary) if interest_summary else "None"
            primary_interest_label = interest_labels.get(top_interest_codes[0], "без яркого интереса") if top_interest_codes else "без яркого интереса"
            primary_goal_label = top_goals[0] if top_goals else "без целей"

            # Prepare metrics for DB and AI
            metrics_dict = {
                'bounce': round(avg_bounce * 100, 1),
                'duration': int(avg_duration),
                'depth': round(avg_depth, 1),
                'top_goals': ", ".join(top_goals) if top_goals else "None",
                'top_interests': top_interests,
                'interest_codes': top_interest_codes,
            }
            
            # AI Naming
            base_name = generate_cohort_name(metrics_dict) or "Целевая группа"
            # Add deterministic descriptor to avoid collisions and clarify intent
            detail_bits = []
            if primary_interest_label and primary_interest_label != "без яркого интереса":
                detail_bits.append(primary_interest_label)
            if primary_goal_label and primary_goal_label != "без целей":
                detail_bits.append(primary_goal_label)
            if detail_bits:
                base_name = f"{base_name} — {', '.join(detail_bits)}"
            if base_name not in combined:
                combined[base_name] = {
                    "count": 0,
                    "bounce_sum": 0.0,
                    "duration_sum": 0.0,
                    "depth_sum": 0.0,
                    "goal_sums": {gc: 0.0 for gc in goal_cols},
                    "interest_sums": {ic: 0.0 for ic in interest_cols},
                    "client_ids": [],  # Для воронок: собираем client_ids пользователей этой когорты
                }
            agg = combined[base_name]
            agg["count"] += len(cluster_data)
            agg["bounce_sum"] += cluster_data['bounce_prob'].sum()
            agg["duration_sum"] += cluster_data['avg_duration'].sum()
            agg["depth_sum"] += cluster_data['avg_depth'].sum()
            # Собираем client_ids для воронок
            agg["client_ids"].extend(list(cluster_data.index.astype(str)))
            for gc in goal_cols:
                agg["goal_sums"][gc] += cluster_data[gc].sum()
            for ic in interest_cols:
                agg["interest_sums"][ic] += cluster_data[ic].sum()

        # Persist combined cohorts (one per name)
        for cohort_name, agg in combined.items():
            total_users = agg["count"]
            if total_users == 0:
                continue

            avg_bounce = agg["bounce_sum"] / total_users
            avg_duration = agg["duration_sum"] / total_users
            avg_depth = agg["depth_sum"] / total_users

            conversions = {}
            top_goals = []
            for gc, sum_val in agg["goal_sums"].items():
                rate = sum_val / total_users
                if rate > 0:
                    code = gc.replace('goal_', '')
                    conversions[code] = round(rate, 4)
                    if rate > 0.05:
                        top_goals.append(f"{code}({int(rate*100)}%)")

            interest_rates = []
            for ic, sum_val in agg["interest_sums"].items():
                rate = sum_val / total_users
                if rate > 0:
                    code = ic.replace('interest_', '')
                    interest_rates.append((code, rate))
            interest_rates.sort(key=lambda x: x[1], reverse=True)
            top_interest_codes = [c for c, _ in interest_rates[:3]]
            interest_summary = []
            for code, rate in interest_rates[:3]:
                label = interest_labels.get(code, code)
                interest_summary.append(f"{label} ({int(rate*100)}%)")
            top_interests = ", ".join(interest_summary) if interest_summary else "None"
            primary_interest_label = interest_labels.get(top_interest_codes[0], "без яркого интереса") if top_interest_codes else "без яркого интереса"
            primary_goal_label = top_goals[0] if top_goals else "без целей"

            metrics_dict = {
                'bounce': round(avg_bounce * 100, 1),
                'duration': int(avg_duration),
                'depth': round(avg_depth, 1),
                'top_goals': ", ".join(top_goals) if top_goals else "None",
                'top_interests': top_interests,
                'interest_codes': top_interest_codes,
            }

            # Enrich name with details (but no numbering; same-name clusters are merged)
            final_name = cohort_name
            detail_bits = []
            if primary_interest_label and primary_interest_label != "без яркого интереса":
                detail_bits.append(primary_interest_label)
            if primary_goal_label and primary_goal_label != "без целей":
                detail_bits.append(primary_goal_label)
            if detail_bits and "—" not in final_name:
                final_name = f"{final_name} — {', '.join(detail_bits)}"

            # Сохраняем client_ids пользователей этой когорты для анализа воронок
            cohort_client_ids = agg.get("client_ids", [])

            UserCohort.objects.create(
                version=version,
                name=final_name,
                avg_bounce_rate=metrics_dict['bounce'],
                avg_duration=metrics_dict['duration'],
                users_count=total_users,
                percentage=total_users / len(user_behavior),
                metrics=metrics_dict,
                conversion_rates=conversions,
                member_client_ids=cohort_client_ids  # Сохраняем client_ids для воронок
            )
            self.stdout.write(f"Сохранена когорта: {final_name} ({total_users} пользователей)")

    def calculate_daily_stats(self, version):
        self.stdout.write("Calculating daily stats...")
        from django.db.models import Count, Avg, Sum, Q
        from django.db.models.functions import TruncDate
        
        stats = VisitSession.objects.filter(version=version).annotate(
            date=TruncDate('start_time')
        ).values('date').annotate(
            total_sessions=Count('id'),
            total_bounces=Count('id', filter=Q(bounced=True)),
            avg_duration=Avg('duration_sec')
        ).order_by('date')
        
        daily_stats = []
        for stat in stats:
            daily_stats.append(DailyStat(
                version=version,
                date=stat['date'],
                total_sessions=stat['total_sessions'],
                total_bounces=stat['total_bounces'],
                avg_duration=stat['avg_duration'] or 0
            ))
        
        DailyStat.objects.bulk_create(daily_stats, ignore_conflicts=True)

    def update_issue_lifecycle(self, version):
        """Фиксирует появление/исчезновение проблем между версиями."""
        self.stdout.write("Updating issue lifecycle...")
        from analytics.models import UXIssue, IssueLifecycle, ProductVersion

        def norm(raw_url: str) -> str:
            if not isinstance(raw_url, str):
                return ""
            parsed = urllib.parse.urlparse(raw_url.strip())
            netloc = parsed.netloc.lower()
            path = (parsed.path or "/").rstrip("/") or "/"
            query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
            for noisy in ['referer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'yclid', '_openstat', 'from', 'ref']:
                query_dict.pop(noisy, None)
            clean_query = urllib.parse.urlencode({k: v[0] if len(v) == 1 else v for k, v in query_dict.items()}, doseq=True)
            scheme = parsed.scheme.lower() if parsed.scheme else ("https" if netloc else "")
            if netloc or scheme:
                return urllib.parse.urlunparse((scheme, netloc, path, '', clean_query, ''))
            return path + (f"?{clean_query}" if clean_query else "")

        prev_version = ProductVersion.objects.filter(release_date__lt=version.release_date).order_by('-release_date').first()
        # очищаем записи для пересчета
        IssueLifecycle.objects.filter(version_first_seen=version).delete()
        IssueLifecycle.objects.filter(version_resolved=version).delete()

        current = UXIssue.objects.filter(version=version)
        prev = UXIssue.objects.none()
        if prev_version:
            prev = UXIssue.objects.filter(version=prev_version)

        prev_index = {(iss.issue_type, norm(iss.location_url)): iss for iss in prev}
        current_index = {(iss.issue_type, norm(iss.location_url)): iss for iss in current}

        lifecycles = []
        for key, issue in current_index.items():
            prev_issue = prev_index.get(key)
            if prev_issue:
                diff = (issue.impact_score or 0) - (prev_issue.impact_score or 0)
                if diff > 1:
                    status = 'REGRESSED'
                elif diff < -1:
                    status = 'IMPROVED'
                else:
                    status = 'PERSISTENT'
                lifecycles.append(IssueLifecycle(
                    issue=issue,
                    version_first_seen=prev_issue.version,
                    version_resolved=None,
                    status=status,
                    impact_change=diff
                ))
            else:
                lifecycles.append(IssueLifecycle(
                    issue=issue,
                    version_first_seen=version,
                    version_resolved=None,
                    status='NEW',
                    impact_change=issue.impact_score or 0
                ))

        for key, prev_issue in prev_index.items():
            if key not in current_index:
                lifecycles.append(IssueLifecycle(
                    issue=prev_issue,
                    version_first_seen=prev_issue.version,
                    version_resolved=version,
                    status='RESOLVED',
                    impact_change=-(prev_issue.impact_score or 0)
                ))

        if lifecycles:
            IssueLifecycle.objects.bulk_create(lifecycles)
            self.stdout.write(f"Lifecycle entries created: {len(lifecycles)}")
        else:
            self.stdout.write("No lifecycle changes detected.")
