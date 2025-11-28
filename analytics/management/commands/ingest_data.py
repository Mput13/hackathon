import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue, DailyStat
from datetime import datetime, timedelta
import os
from analytics.ai_service import analyze_issue_with_ai
import traceback

class Command(BaseCommand):
    help = 'Ingests Parquet data from Yandex Metrica and runs UX analysis'

    def add_arguments(self, parser):
        parser.add_argument('--visits', type=str, help='Path to visits parquet file')
        parser.add_argument('--hits', type=str, help='Path to hits parquet file')
        parser.add_argument('--product-version', type=str, help='Version name (e.g., "v1.0")')
        parser.add_argument('--year', type=int, help='Year of data (e.g., 2022)')

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
            # 1. Create or Get Version
            self.stdout.write("DEBUG: Creating ProductVersion...")
            version, created = ProductVersion.objects.get_or_create(
                name=version_name,
                defaults={'release_date': datetime(year, 1, 1), 'is_active': True}
            )
            self.stdout.write(f"DEBUG: ProductVersion created: {version.id}")

            # 2. Load Data (Using Pandas)
            self.stdout.write(f"Loading Parquet files from {visits_path}...")
            if not os.path.exists(visits_path):
                 self.stdout.write(self.style.ERROR(f"File not found: {visits_path}"))
                 return
            
            # OPTIMIZATION: Read only necessary columns
            # Visits has visitID
            visits_columns = [
                'ym:s:visitID', 'ym:s:clientID', 'ym:s:dateTime', 
                'ym:s:visitDuration', 'ym:s:deviceCategory', 'ym:s:referer', 
                'ym:s:bounce', 'ym:s:pageViews'
            ]
            df_visits = pd.read_parquet(visits_path, columns=visits_columns)
            self.stdout.write(f"DEBUG: Visits loaded. Shape: {df_visits.shape}")
            
            # Hits DOES NOT have visitID, using clientID instead
            hits_columns = [
                'ym:pv:clientID', 'ym:pv:dateTime', 'ym:pv:URL', 'ym:pv:title'
            ]
            df_hits = pd.read_parquet(hits_path, columns=hits_columns)
            self.stdout.write(f"DEBUG: Hits loaded. Shape: {df_hits.shape}")

            # 3. Process Visits (Sessions)
            self.stdout.write("Processing Visits...")
            # Sampling for MVP speed
            if len(df_visits) > 10000:
                self.stdout.write(f"Sampling 10k visits from {len(df_visits)}...")
                df_visits = df_visits.head(10000)
                # Filter hits by clientIDs from the sample
                client_ids = df_visits['ym:s:clientID'].unique()
                df_hits = df_hits[df_hits['ym:pv:clientID'].isin(client_ids)]

            # Bulk Create Sessions
            visit_objects = []
            visit_map_by_client = {} # client_id -> visit_id (last one)
            
            for _, row in df_visits.iterrows():
                v_id = str(row.get('ym:s:visitID', ''))
                c_id = str(row.get('ym:s:clientID', ''))
                
                visit = VisitSession(
                    version=version,
                    visit_id=v_id,
                    client_id=c_id,
                    start_time=pd.to_datetime(row.get('ym:s:dateTime')),
                    duration_sec=int(row.get('ym:s:visitDuration', 0)),
                    device_category=row.get('ym:s:deviceCategory', 'unknown'),
                    source=row.get('ym:s:referer', ''),
                    bounced=bool(row.get('ym:s:bounce', 0)),
                    page_views=int(row.get('ym:s:pageViews', 0))
                )
                visit_objects.append(visit)
                # Store for linking hits (rough approx: latest visit for client)
                visit_map_by_client[c_id] = visit
            
            self.stdout.write("DEBUG: Saving visits to DB...")
            VisitSession.objects.bulk_create(visit_objects, ignore_conflicts=True)
            self.stdout.write(f"Created {len(visit_objects)} sessions.")

            # Re-fetch visits from DB to get PKs
            # Optimization: Get dict {client_id: visit_pk}
            # Warning: This is imperfect if one client has multiple visits, but good enough for MVP
            # to link hits to *some* session of that user.
            db_visits = VisitSession.objects.filter(version=version).values('id', 'client_id')
            client_to_visit_pk = {v['client_id']: v['id'] for v in db_visits}

            # 4. Process Hits
            self.stdout.write("Processing Hits...")
            hit_objects = []
            for _, row in df_hits.iterrows():
                c_id = str(row.get('ym:pv:clientID', ''))
                
                # Link to session if possible, else skip (or create orphan)
                if c_id in client_to_visit_pk:
                    hit = PageHit(
                        session_id=client_to_visit_pk[c_id],
                        timestamp=pd.to_datetime(row.get('ym:pv:dateTime')),
                        url=row.get('ym:pv:URL', ''),
                        page_title=row.get('ym:pv:title', ''),
                        action_type='view',
                    )
                    hit_objects.append(hit)
            
            self.stdout.write("DEBUG: Saving hits to DB...")
            PageHit.objects.bulk_create(hit_objects, batch_size=5000)
            self.stdout.write(f"Created {len(hit_objects)} hits.")

            # 5. Run Analysis (Heuristics)
            # Pass client_to_visit_pk map or just use DFs
            self.run_analysis(version, df_hits, df_visits)

            # 6. Pre-calculate Daily Stats
            self.calculate_daily_stats(version)

            self.stdout.write(self.style.SUCCESS(f"Ingestion and analysis complete for {version_name}"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CRITICAL ERROR: {e}"))
            traceback.print_exc()

    def run_analysis(self, version, df_hits, df_visits):
        self.stdout.write("Running UX Analysis...")
        issues = []

        # A. Rage Clicks Detection (using clientID grouping instead of visitID)
        df_hits['timestamp'] = pd.to_datetime(df_hits['ym:pv:dateTime'])
        
        df_hits_sorted = df_hits.sort_values(['ym:pv:clientID', 'timestamp'])
        df_hits_sorted['time_diff'] = df_hits_sorted.groupby('ym:pv:clientID')['timestamp'].diff().dt.total_seconds()
        df_hits_sorted['prev_url'] = df_hits_sorted.groupby('ym:pv:clientID')['ym:pv:URL'].shift()
        
        rage_clicks = df_hits_sorted[
            (df_hits_sorted['time_diff'] < 2) & 
            (df_hits_sorted['ym:pv:URL'] == df_hits_sorted['prev_url'])
        ]
        
        if not rage_clicks.empty:
            rage_stats = rage_clicks['ym:pv:URL'].value_counts().head(5)
            for url, count in rage_stats.items():
                self.stdout.write(f"DEBUG: Found Rage Click on {url} ({count})")
                ai_text = analyze_issue_with_ai(
                     issue_type='RAGE_CLICK',
                     location=url,
                     metrics_context=f"Количество событий: {count}"
                 )
                issues.append(UXIssue(
                    version=version,
                    issue_type='RAGE_CLICK',
                    severity='WARNING',
                    description=f"Detected {count} rapid reloads/clicks on this page.",
                    location_url=url,
                    affected_sessions=count,
                    impact_score=min(count * 0.1, 10.0),
                    ai_hypothesis=ai_text
                ))

        # B. High Bounce Rate (stays same, uses visits DF)
        bounced_visits = df_visits[df_visits['ym:s:visitDuration'] < 15]['ym:s:clientID'] # using clientID link
        bounced_hits = df_hits[df_hits['ym:pv:clientID'].isin(bounced_visits)]
        
        if not bounced_hits.empty:
            bounce_stats = bounced_hits['ym:pv:URL'].value_counts().head(5)
            for url, count in bounce_stats.items():
                 self.stdout.write(f"DEBUG: Found High Bounce on {url} ({count})")
                 ai_text = analyze_issue_with_ai(
                     issue_type='HIGH_BOUNCE',
                     location=url,
                     metrics_context=f"Количество отказов: {count}"
                 )
                 issues.append(UXIssue(
                    version=version,
                    issue_type='HIGH_BOUNCE',
                    severity='CRITICAL',
                    description=f"High bounce rate detected. {count} users left immediately.",
                    location_url=url,
                    affected_sessions=count,
                    impact_score=min(count * 0.2, 10.0),
                    ai_hypothesis=ai_text
                ))

        # C. Loops (using clientID)
        loop_counts = df_hits.groupby(['ym:pv:clientID', 'ym:pv:URL']).size()
        loops = loop_counts[loop_counts > 3]
        
        if not loops.empty:
            loop_urls = loops.index.get_level_values('ym:pv:URL').value_counts().head(5)
            for url, count in loop_urls.items():
                self.stdout.write(f"DEBUG: Found Loop on {url} ({count})")
                ai_text = analyze_issue_with_ai(
                     issue_type='LOOPING',
                     location=url,
                     metrics_context=f"Количество зацикливаний: {count}"
                 )
                issues.append(UXIssue(
                    version=version,
                    issue_type='LOOPING',
                    severity='WARNING',
                    description=f"Users keep returning to this page ({count} loop events).",
                    location_url=url,
                    affected_sessions=count,
                    impact_score=min(count * 0.15, 10.0),
                    ai_hypothesis=ai_text
                ))

        UXIssue.objects.bulk_create(issues)
        self.stdout.write(f"Detected {len(issues)} UX issues.")

    def calculate_daily_stats(self, version):
        # ... (keep existing)
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
