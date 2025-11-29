"""
Helper functions extracted from ingest_data.py to keep the management command lean.
They operate on the Command instance (cmd) to reuse stdout/style helpers.
"""
import urllib.parse
import os
from collections import defaultdict
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from analytics.models import PageMetrics, UXIssue, UserCohort, VisitSession
from analytics.ai_service import analyze_issue_with_ai, generate_cohort_name

MIN_PAGE_VIEWS_FOR_PAGE_ALERT = int(os.environ.get("MIN_PAGE_VIEWS_FOR_PAGE_ALERT", "30"))

def run_analysis(cmd, version, df_hits, df_visits):
    """Запускает анализ UX-проблем с AI-гипотезами"""
    cmd.stdout.write("Running UX Analysis...")
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
            trend = cmd._calculate_trend('RAGE_CLICK', norm_url, impact)
            priority = cmd._calculate_priority('WARNING', impact, count, trend)
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
                recommended_specialists=cmd._recommend_specialists('RAGE_CLICK')
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
            trend = cmd._calculate_trend('LOOPING', norm_url, impact)
            priority = cmd._calculate_priority('WARNING', impact, count, trend)
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
                recommended_specialists=cmd._recommend_specialists('LOOPING')
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
            unique_nodes = set(path_tuple)
            if len(unique_nodes) == 2:
                return tuple(sorted(unique_nodes))
            return path_tuple

        def canonical_loop_display(path_tuple):
            unique_nodes = set(path_tuple)
            if len(unique_nodes) == 2:
                a, b = sorted(unique_nodes)
                return f"{a} -> {b} -> {a}"
            return " -> ".join(path_tuple)

        loop_events = []
        for client_id, group in df_hits_sorted.groupby('ym:pv:clientID'):
            urls = group['ym:pv:URL'].tolist()
            for idx in range(len(urls)):
                for window in (2, 3):
                    if idx >= window:
                        seq = urls[idx - window:idx + 1]
                        norm_seq = [normalize_issue_url(u) for u in seq]
                        if norm_seq[0] and norm_seq[-1] and norm_seq[0] == norm_seq[-1] and len(set(norm_seq)) > 1:
                            key = canonical_loop_key(tuple(norm_seq))
                            display = canonical_loop_display(tuple(norm_seq))
                            loop_events.append((key, display, client_id))

        if loop_events:
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
                target_url = path_key[1] if len(path_key) > 1 else path_key[0]
                nav_back_targets.add(target_url)
                page_metrics = PageMetrics.objects.filter(version=version, url=target_url).first()
                metrics_context = f"Навигационный цикл: {loop_path}. Повторений: {pattern_count}, пользователей: {users_count}"
                impact = min(pattern_count * 0.12, 10.0)
                trend = cmd._calculate_trend('NAVIGATION_BACK', loop_path, impact)
                priority = cmd._calculate_priority('WARNING', impact, users_count, trend)

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
                    recommended_specialists=cmd._recommend_specialists('LOOPING')
                ))

    # E. HIGH_BOUNCE
    bounced_visits = df_visits[df_visits['ym:s:visitDuration'] < 15]['ym:s:clientID']
    bounced_hits = df_hits[df_hits['ym:pv:clientID'].isin(bounced_visits)].copy()

    if not bounced_hits.empty:
        bounced_hits['norm_url'] = bounced_hits['ym:pv:URL'].apply(normalize_issue_url)
        bounce_stats = bounced_hits['norm_url'].value_counts().head(5)
        for norm_url, count in bounce_stats.items():
             if not norm_url:
                 continue
             if norm_url in nav_back_targets:
                 continue  # already covered
             representative_url = pick_representative_url(bounced_hits, 'norm_url', norm_url)
             page_metrics = PageMetrics.objects.filter(version=version, url=representative_url).first()
             if not page_metrics:
                 page_metrics = PageMetrics.objects.filter(version=version, url=norm_url).first()
             impact = min(count * 0.2, 10.0)
             trend = cmd._calculate_trend('HIGH_BOUNCE', norm_url, impact)
             priority = cmd._calculate_priority('CRITICAL', impact, count, trend)
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
                recommended_specialists=cmd._recommend_specialists('HIGH_BOUNCE')
            ))

    # F. FORM_FIELD_ERRORS
    form_pattern = r'/form|/apply|/request|/anket|/zayav'
    form_hits = df_hits[df_hits['ym:pv:URL'].astype(str).str.contains(form_pattern, na=False, regex=True)]

    if not form_hits.empty:
        # Нормализуем время и делим на «квазисессии» с разрывом >30 минут, чтобы не суммировать дни
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
        form_sessions = form_sessions[form_sessions['duration'] <= 7200]

        long_form = form_sessions[form_sessions['duration'] > 60]
        if not long_form.empty:
            long_form_clients = long_form['client_id']
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

    # G. FUNNEL_DROPOFF
    funnel_steps = ['/', '/lists', '/rating', '/apply']

    for i in range(len(funnel_steps) - 1):
        step1_url = normalize_issue_url(funnel_steps[i])
        step2_url = normalize_issue_url(funnel_steps[i + 1])

        step1_users = set(df_hits[df_hits['norm_url'] == step1_url]['ym:pv:clientID'])
        step2_users = set(df_hits[df_hits['norm_url'] == step2_url]['ym:pv:clientID'])

        if step1_users and len(step1_users) >= 50:
            conversion = len(step2_users & step1_users) / len(step1_users)

            if conversion < 0.3:
                lost_users = len(step1_users) - len(step2_users & step1_users)
                page_metrics = PageMetrics.objects.filter(version=version, url=step1_url).first() or PageMetrics.objects.filter(version=version, url=funnel_steps[i]).first()
                metrics_context = f"Конверсия {step1_url} -> {step2_url}: {conversion*100:.1f}%, Потеряно пользователей: {lost_users}"

                ai_text = analyze_issue_with_ai(
                    issue_type='FUNNEL_DROPOFF',
                    location=step1_url,
                    metrics_context=metrics_context,
                    page_title=page_metrics.page_title if page_metrics else None,
                    page_metrics={'avg_time': page_metrics.avg_time_on_page if page_metrics else None} if page_metrics else None,
                    dominant_cohort=page_metrics.dominant_cohort if page_metrics else None,
                    dominant_device=page_metrics.dominant_device if page_metrics else None
                )
                issues.append(UXIssue(
                    version=version,
                    issue_type='FUNNEL_DROPOFF',
                    severity='CRITICAL',
                    description=f"Критический отвал между {step1_url} и {step2_url}. Конверсия: {conversion*100:.1f}%.",
                    location_url=step1_url,
                    affected_sessions=lost_users,
                    impact_score=min(lost_users * 0.2, 10.0),
                    ai_hypothesis=ai_text
                ))

    # H. DEAD_CLICK: страницы с высоким выходом и почти нулевым вовлечением
    dead_candidates = PageMetrics.objects.filter(
        version=version,
        total_views__gte=MIN_PAGE_VIEWS_FOR_PAGE_ALERT,
        exit_rate__gte=60,
        avg_time_on_page__lte=5
    ).order_by('-exit_rate')[:5]
    for metric in dead_candidates:
        if metric.avg_scroll_depth is not None and metric.avg_scroll_depth > 20:
            continue
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

    UXIssue.objects.bulk_create(issues)
    cmd.stdout.write(f"Найдено {len(issues)} UX-проблем.")


def segment_users_into_cohorts(cmd, version, df_visits, df_hits, goals_config):
    cmd.stdout.write("--- Starting User Segmentation ---")

    # 1. Base User Metrics
    user_behavior = df_visits.groupby('ym:s:clientID').agg({
        'ym:s:visitDuration': 'mean',
        'ym:s:pageViews': 'mean',
        'ym:s:visitID': 'count',
        'ym:s:bounce': 'mean'
    }).rename(columns={
        'ym:s:visitDuration': 'avg_duration',
        'ym:s:pageViews': 'avg_depth',
        'ym:s:visitID': 'total_visits',
        'ym:s:bounce': 'bounce_prob'
    })

    # 2. Join hits to get top interests (titles) and clicks on APPLY-ish buttons
    df_hits['title_clean'] = df_hits['ym:pv:title'].fillna('').str.lower()
    top_titles = df_hits['title_clean'].value_counts().head(20).index.tolist()
    for title in top_titles:
        user_behavior[f"title_{title[:30]}"] = df_hits[df_hits['title_clean'] == title].groupby('ym:pv:clientID')['ym:pv:URL'].transform('count')

    def contains_apply(url):
        if not isinstance(url, str):
            return False
        return any(word in url for word in ['/apply', 'submit', 'anket', 'zayav'])

    df_hits['is_apply_like'] = df_hits['ym:pv:URL'].apply(contains_apply)
    apply_counts = df_hits[df_hits['is_apply_like']].groupby('ym:pv:clientID')['is_apply_like'].count()

    user_behavior = user_behavior.join(apply_counts.rename('apply_clicks'), how='left')
    user_behavior['apply_clicks'] = user_behavior['apply_clicks'].fillna(0)

    # 3. Goals (если есть)
    if 'ym:s:goalsID' in df_visits.columns:
        user_behavior['goal_any'] = df_visits['ym:s:goalsID'].apply(lambda g: 1 if g and g != [] else 0)
    else:
        user_behavior['goal_any'] = 0

    user_behavior = user_behavior.fillna(0)

    # 4. Scale and Cluster
    feature_cols = [c for c in user_behavior.columns if c not in ['goal_any']]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(user_behavior[feature_cols])

    n_clusters = min(5, max(2, len(user_behavior) // 500))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(X_scaled)

    user_behavior['cluster'] = labels

    # 5. Summaries
    cluster_metrics = defaultdict(lambda: defaultdict(float))
    cluster_users = defaultdict(list)

    for idx, row in user_behavior.iterrows():
        cluster_id = row['cluster']
        cluster_users[cluster_id].append(idx)
        cluster_metrics[cluster_id]['duration_sum'] += row['avg_duration']
        cluster_metrics[cluster_id]['depth_sum'] += row['avg_depth']
        cluster_metrics[cluster_id]['visits_sum'] += row['total_visits']
        cluster_metrics[cluster_id]['bounce_sum'] += row['bounce_prob']
        cluster_metrics[cluster_id]['count'] += 1
        cluster_metrics[cluster_id]['goals'] += row['goal_any']

    # 6. Build cohorts
    UserCohort.objects.filter(version=version).delete()

    for cluster_id, agg in cluster_metrics.items():
        total_users = agg['count']
        avg_duration = agg['duration_sum'] / total_users if total_users else 0
        avg_depth = agg['depth_sum'] / total_users if total_users else 0
        avg_bounce = agg['bounce_sum'] / total_users if total_users else 0
        conversions = {
            'apply_button_clicks': agg.get('apply_clicks', 0) / total_users if total_users else 0,
            'goal_any': agg.get('goals', 0) / total_users if total_users else 0,
        }

        cohort_name = generate_cohort_name(avg_duration, avg_depth, avg_bounce, conversions)

        titles_vector = [col for col in user_behavior.columns if col.startswith('title_')]
        title_counts = user_behavior[user_behavior['cluster'] == cluster_id][titles_vector].sum().sort_values(ascending=False)
        top_titles = title_counts.head(3)
        top_interests = [t.replace('title_', '') for t in top_titles.index]
        top_interest_codes = "; ".join(top_interests)

        top_goals = []
        if 'ym:s:goalsID' in df_visits.columns:
            goals_lists = df_visits[df_visits['ym:s:clientID'].isin(cluster_users[cluster_id])]['ym:s:goalsID']
            for goals_raw in goals_lists:
                if isinstance(goals_raw, list):
                    top_goals.extend(goals_raw)
            top_goals = list(dict.fromkeys(top_goals))[:3]

        metrics_dict = {
            'bounce': round(avg_bounce * 100, 1),
            'duration': int(avg_duration),
            'depth': round(avg_depth, 1),
            'top_goals': ", ".join(top_goals) if top_goals else "None",
            'top_interests': top_interests,
            'interest_codes': top_interest_codes,
        }

        final_name = cohort_name
        detail_bits = []
        primary_interest_label = top_interests[0] if top_interests else None
        primary_goal_label = goals_config[0]['name'] if goals_config else None
        if primary_interest_label and primary_interest_label != "без яркого интереса":
            detail_bits.append(primary_interest_label)
        if primary_goal_label and primary_goal_label != "без целей":
            detail_bits.append(primary_goal_label)
        if detail_bits and "—" not in final_name:
            final_name = f"{final_name} — {', '.join(detail_bits)}"

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
            member_client_ids=cohort_client_ids
        )
        cmd.stdout.write(f"Saved cohort: {final_name} ({total_users} users)")


__all__ = ['run_analysis', 'segment_users_into_cohorts']
