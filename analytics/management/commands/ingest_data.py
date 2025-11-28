import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue, DailyStat, UserCohort
from datetime import datetime, timedelta
import os
from analytics.ai_service import analyze_issue_with_ai, generate_cohort_name
from analytics.utils import GoalParser
import traceback
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

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

            # 2. Load Data (Using Pandas)
            self.stdout.write(f"Loading Parquet files from {visits_path}...")
            if not os.path.exists(visits_path):
                 self.stdout.write(self.style.ERROR(f"File not found: {visits_path}"))
                 return
            
            # Visits columns
            visits_columns = [
                'ym:s:visitID', 'ym:s:clientID', 'ym:s:dateTime', 
                'ym:s:visitDuration', 'ym:s:deviceCategory', 'ym:s:referer', 
                'ym:s:bounce', 'ym:s:pageViews'
            ]
            # Try to add goalsID if available (it might not be in all exports)
            # We'll handle the check during read or by checking schema first, 
            # but for simplicity here we'll try to read it if we can't check easily.
            # Actually, let's trust standard Metrika export.
            visits_columns.append('ym:s:goalsID') 

            try:
                df_visits = pd.read_parquet(visits_path, columns=visits_columns)
            except Exception:
                self.stdout.write("Warning: 'ym:s:goalsID' not found or error reading it. Goal matching by ID disabled.")
                visits_columns.remove('ym:s:goalsID')
                df_visits = pd.read_parquet(visits_path, columns=visits_columns)

            # Ensure timestamps are timezone-aware (UTC) to avoid Django naive datetime warnings
            df_visits['ym:s:dateTime'] = pd.to_datetime(df_visits['ym:s:dateTime'], utc=True, errors='coerce')
            # Normalize client IDs to string for consistent joins with hits
            df_visits['client_id_norm'] = df_visits['ym:s:clientID'].astype(str)
            df_visits['ym:s:clientID'] = df_visits['client_id_norm']
            self.stdout.write(f"DEBUG: Visits loaded. Shape: {df_visits.shape}")
            
            # Hits columns
            hits_columns = [
                'ym:pv:clientID', 'ym:pv:dateTime', 'ym:pv:URL', 'ym:pv:title'
            ]
            df_hits = pd.read_parquet(hits_path, columns=hits_columns)
            df_hits['ym:pv:dateTime'] = pd.to_datetime(df_hits['ym:pv:dateTime'], utc=True, errors='coerce')
            df_hits['client_id_norm'] = df_hits['ym:pv:clientID'].astype(str)
            df_hits['ym:pv:clientID'] = df_hits['client_id_norm']
            self.stdout.write(f"DEBUG: Hits loaded. Shape: {df_hits.shape}")

            # 3. Process Visits (Sessions)
            self.stdout.write("Processing Visits...")
            
            # Sampling logic (Optional, kept from previous version)
            if len(df_visits) > 10000:
                self.stdout.write(f"Sampling 10k visits from {len(df_visits)}...")
                df_visits = df_visits.head(10000)
                client_ids = df_visits['client_id_norm'].unique()
                df_hits = df_hits[df_hits['client_id_norm'].isin(client_ids)]

            # Bulk Create Sessions
            visit_objects = []
            visit_map_by_client = {} 
            
            for _, row in df_visits.iterrows():
                v_id = str(row.get('ym:s:visitID', ''))
                c_id = str(row.get('client_id_norm', ''))
                
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
                visit_map_by_client[c_id] = visit
            
            self.stdout.write("DEBUG: Saving visits to DB...")
            VisitSession.objects.bulk_create(visit_objects, ignore_conflicts=True)
            self.stdout.write(f"Created {len(visit_objects)} sessions.")

            db_visits = VisitSession.objects.filter(version=version).values('id', 'client_id')
            client_to_visit_pk = {v['client_id']: v['id'] for v in db_visits}

            # 4. Process Hits
            self.stdout.write("Processing Hits...")
            hit_objects = []
            for _, row in df_hits.iterrows():
                c_id = str(row.get('client_id_norm', ''))
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
            self.run_analysis(version, df_hits, df_visits)

            # 6. Segment Users into Cohorts (New Logic)
            self.segment_users_into_cohorts(version, df_visits, df_hits, goals_config)

            # 7. Pre-calculate Daily Stats
            self.calculate_daily_stats(version)

            self.stdout.write(self.style.SUCCESS(f"Ingestion and analysis complete for {version_name}"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CRITICAL ERROR: {e}"))
            traceback.print_exc()

    def run_analysis(self, version, df_hits, df_visits):
        # ... (Previous logic for Rage Clicks, Bounce, Loops - Kept as is)
        self.stdout.write("Running UX Analysis...")
        issues = []

        # A. Rage Clicks Detection
        df_hits['timestamp'] = pd.to_datetime(df_hits['ym:pv:dateTime'], utc=True)
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
                # self.stdout.write(f"DEBUG: Found Rage Click on {url} ({count})")
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

        # B. High Bounce Rate
        bounced_visits = df_visits[df_visits['ym:s:visitDuration'] < 15]['ym:s:clientID']
        bounced_hits = df_hits[df_hits['ym:pv:clientID'].isin(bounced_visits)]
        
        if not bounced_hits.empty:
            bounce_stats = bounced_hits['ym:pv:URL'].value_counts().head(5)
            for url, count in bounce_stats.items():
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

        # C. Loops
        loop_counts = df_hits.groupby(['ym:pv:clientID', 'ym:pv:URL']).size()
        loops = loop_counts[loop_counts > 3]
        
        if not loops.empty:
            loop_urls = loops.index.get_level_values('ym:pv:URL').value_counts().head(5)
            for url, count in loop_urls.items():
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
            self.stdout.write("No users to segment.")
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
        base_name_counts = {}
        
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
            count = base_name_counts.get(base_name, 0) + 1
            base_name_counts[base_name] = count
            cohort_name = f"{base_name} #{count}"
            
            UserCohort.objects.create(
                version=version,
                name=cohort_name,
                avg_bounce_rate=metrics_dict['bounce'],
                avg_duration=metrics_dict['duration'],
                users_count=len(cluster_data),
                percentage=len(cluster_data) / len(user_behavior),
                metrics=metrics_dict,
                conversion_rates=conversions
            )
            self.stdout.write(f"Saved cohort: {cohort_name} ({len(cluster_data)} users)")

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
