from django.shortcuts import render
from django.db.models import Sum, Avg, Count, Case, When, IntegerField
from django.db.models.functions import Cast
from django.http import JsonResponse
from .models import ProductVersion, VisitSession, UXIssue, DailyStat, UserCohort, PageMetrics
from .utils import get_readable_page_name
import urllib.parse


def _normalize_issue_url(raw_url: str) -> str:
    """
    Нормализация URL для дедупликации: убираем utm/referer/trailing slash.
    Повторяет логику ingest, чтобы корректно сравнивать между версиями.
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

TREND_LABELS = {
    'new': 'Новая проблема',
    'worse': 'Ухудшилась',
    'improved': 'Улучшилась',
    'stable': 'Без изменений',
}


def get_trend_label(trend_code: str) -> str:
    """Преобразует код динамики в человекочитаемую подпись."""
    if not trend_code:
        return TREND_LABELS['new']
    return TREND_LABELS.get(trend_code, trend_code)

def dashboard(request):
    """Main Dashboard View"""
    versions = ProductVersion.objects.all()
    
    # Get stats for each version
    version_stats = []
    for version in versions:
        stats = VisitSession.objects.filter(version=version).aggregate(
            total_visits=Count('id'),
            avg_duration=Avg('duration_sec'),
            # Postgres requires explicit cast for boolean averaging
            bounce_rate=Avg(Cast('bounced', output_field=IntegerField()))
        )
        
        issue_count = UXIssue.objects.filter(version=version).count()
        critical_issues = UXIssue.objects.filter(version=version, severity='CRITICAL').count()
        
        version_stats.append({
            'version': version,
            'total_visits': stats['total_visits'] or 0,
            'avg_duration': round(stats['avg_duration'] or 0, 1),
            'bounce_rate': round((stats['bounce_rate'] or 0) * 100, 1),
            'issue_count': issue_count,
            'critical_issues': critical_issues
        })
    
    # Get recent issues for the dashboard list
    # Fallback to empty list if no issues found
    recent_issues = UXIssue.objects.select_related('version').order_by('-created_at')[:5]
    
    # Convert QuerySet to list to allow modifying attributes
    recent_issues_list = []
    for issue in recent_issues:
        issue.readable_location = get_readable_page_name(issue.location_url)
        issue.trend_label = get_trend_label(issue.trend)
        recent_issues_list.append(issue)

    context = {
        'version_stats': version_stats,
        'recent_issues': recent_issues_list
    }
    return render(request, 'analytics/dashboard.html', context)

def compare_versions(request):
    """Compare View (v1 vs v2)"""
    v1_id = request.GET.get('v1')
    v2_id = request.GET.get('v2')
    
    all_versions = ProductVersion.objects.all()
    
    # If no specific versions selected, try to pick the last two
    if not v1_id or not v2_id:
        if all_versions.count() >= 2:
            # Default: Compare latest (v2) vs previous (v1)
            # Assuming ID order or Release Date order implies version order
            ordered_versions = all_versions.order_by('release_date')
            v1_id = ordered_versions[0].id # Oldest
            v2_id = ordered_versions[ordered_versions.count()-1].id # Newest
    
    context = {
        'versions': all_versions,
        'selected_v1': int(v1_id) if v1_id else None,
        'selected_v2': int(v2_id) if v2_id else None,
    }
    
    if v1_id and v2_id:
        try:
            v1 = ProductVersion.objects.get(id=v1_id)
            v2 = ProductVersion.objects.get(id=v2_id)
            
            stats_v1 = VisitSession.objects.filter(version=v1).aggregate(
                visits=Count('id'),
                bounce=Avg(Cast('bounced', output_field=IntegerField())),
                duration=Avg('duration_sec')
            )
            
            stats_v2 = VisitSession.objects.filter(version=v2).aggregate(
                visits=Count('id'),
                bounce=Avg(Cast('bounced', output_field=IntegerField())),
                duration=Avg('duration_sec')
            )
            
            # Calculate Diff
            v1_visits = stats_v1['visits'] or 0
            v2_visits = stats_v2['visits'] or 0
            
            v1_bounce = (stats_v1['bounce'] or 0) * 100
            v2_bounce = (stats_v2['bounce'] or 0) * 100
            
            v1_dur = stats_v1['duration'] or 0
            v2_dur = stats_v2['duration'] or 0

            v1_cohorts = list(UserCohort.objects.filter(version=v1).order_by('-percentage'))
            v2_cohorts = list(UserCohort.objects.filter(version=v2).order_by('-percentage'))
            for c in v1_cohorts:
                c.display_percentage = (c.percentage or 0) * 100
            for c in v2_cohorts:
                c.display_percentage = (c.percentage or 0) * 100

            # Build diff for issues
            issues_v1 = UXIssue.objects.filter(version=v1)
            issues_v2 = UXIssue.objects.filter(version=v2)
            def index_issues(qs):
                data = {}
                for it in qs:
                    key = (it.issue_type, _normalize_issue_url(it.location_url))
                    data[key] = it
                return data
            idx_v1 = index_issues(issues_v1)
            idx_v2 = index_issues(issues_v2)
            issues_diff = []
            for key, issue in idx_v2.items():
                prev = idx_v1.get(key)
                if not prev:
                    status = "new"
                    impact_diff = issue.impact_score
                else:
                    impact_diff = (issue.impact_score or 0) - (prev.impact_score or 0)
                    if impact_diff > 1:
                        status = "worse"
                    elif impact_diff < -1:
                        status = "improved"
                    else:
                        status = "stable"
                issues_diff.append({
                    'issue': issue,
                    'status': status,
                    'impact_diff': round(impact_diff, 2),
                    'location_readable': get_readable_page_name(issue.location_url),
                })
            for key, issue in idx_v1.items():
                if key not in idx_v2:
                    issues_diff.append({
                        'issue': issue,
                        'status': 'resolved',
                        'impact_diff': -(issue.impact_score or 0),
                        'location_readable': get_readable_page_name(issue.location_url),
                    })
            issues_diff = sorted(issues_diff, key=lambda x: (-abs(x['impact_diff']), x['issue'].severity))

            # Build diff for pages
            pages_v1 = { _normalize_issue_url(m.url): m for m in PageMetrics.objects.filter(version=v1) }
            pages_v2 = { _normalize_issue_url(m.url): m for m in PageMetrics.objects.filter(version=v2) }
            page_diff = []
            keys = set(pages_v1.keys()) | set(pages_v2.keys())
            for key in keys:
                m1 = pages_v1.get(key)
                m2 = pages_v2.get(key)
                views1 = m1.total_views if m1 else 0
                views2 = m2.total_views if m2 else 0
                max_views = max(views1, views2)
                if max_views and max_views < 20:
                    continue  # игнорируем шумные страницы с малым трафиком
                status = 'stable'
                exit_diff = 0
                time_diff = 0
                if m1 and not m2:
                    status = 'removed'
                elif m2 and not m1:
                    status = 'new'
                else:
                    exit_diff = (m2.exit_rate or 0) - (m1.exit_rate or 0)
                    time_diff = (m2.avg_time_on_page or 0) - (m1.avg_time_on_page or 0)
                    # ограничиваем экстремальные выбросы
                    if time_diff > 1800:
                        time_diff = 1800
                    if time_diff < -1800:
                        time_diff = -1800
                    if abs(exit_diff) > 5 or abs(time_diff) > 5:
                        status = 'changed'
                readable = get_readable_page_name(m2.url if m2 else m1.url)
                page_diff.append({
                    'key': key,
                    'status': status,
                    'exit_diff': round(exit_diff, 1),
                    'time_diff': round(time_diff, 1),
                    'v1': m1,
                    'v2': m2,
                    'readable': readable,
                })
            page_diff = sorted(page_diff, key=lambda x: (-abs(x['exit_diff']), x['readable']))

            # Diff for cohorts (by name)
            coh_v1 = {c.name: c for c in v1_cohorts}
            coh_v2 = {c.name: c for c in v2_cohorts}
            cohorts_diff = []
            for name, c2 in coh_v2.items():
                c1 = coh_v1.get(name)
                if not c1:
                    cohorts_diff.append({'name': name, 'status': 'new', 'v1': None, 'v2': c2})
                else:
                    cohorts_diff.append({'name': name, 'status': 'changed', 'v1': c1, 'v2': c2})
            for name, c1 in coh_v1.items():
                if name not in coh_v2:
                    cohorts_diff.append({'name': name, 'status': 'removed', 'v1': c1, 'v2': None})

            comparison = {
                'v1': v1, 'v2': v2,
                'visits_diff': int(v2_visits - v1_visits),
                'bounce_diff': round(v2_bounce - v1_bounce, 1),
                'duration_diff': round(v2_dur - v1_dur, 1),
                'stats_v1': {'visits': v1_visits, 'bounce': round(v1_bounce, 1), 'duration': round(v1_dur, 1)},
                'stats_v2': {'visits': v2_visits, 'bounce': round(v2_bounce, 1), 'duration': round(v2_dur, 1)},
                'v1_cohorts': v1_cohorts,
                'v2_cohorts': v2_cohorts,
                'issues_diff': issues_diff[:20],
                'pages_diff': page_diff[:20],
                'cohorts_diff': cohorts_diff[:20],
            }
            context['comparison'] = comparison
        except ProductVersion.DoesNotExist:
            pass # Just don't show comparison if IDs are invalid
        
    return render(request, 'analytics/compare.html', context)

def issues_list(request):
    """Full List of Detected UX Issues"""
    version_id = request.GET.get('version')
    severity = request.GET.get('severity')
    issue_type = request.GET.get('issue_type')
    
    issues = UXIssue.objects.select_related('version').all().order_by('-impact_score', '-created_at')
    
    if version_id:
        issues = issues.filter(version_id=version_id)
    if severity:
        issues = issues.filter(severity=severity)
    if issue_type:
        issues = issues.filter(issue_type=issue_type)
        
    # Prepare readable names
    # Note: For very large lists, this might be slow, but for <1000 issues it's fine
    issues_list = []
    for issue in issues:
        issue.readable_location = get_readable_page_name(issue.location_url)
        issue.trend_label = get_trend_label(issue.trend)
        issues_list.append(issue)
        
    context = {
        'issues': issues_list,
        'versions': ProductVersion.objects.all(),
        'issue_types': UXIssue.PROBLEM_TYPES,
        'selected_version': int(version_id) if version_id else None,
        'selected_severity': severity,
        'selected_issue_type': issue_type
    }
    return render(request, 'analytics/issues.html', context)

def api_versions(request):
    """JSON: список версий продукта"""
    versions = ProductVersion.objects.all().order_by('release_date')
    data = [
        {
            'id': v.id,
            'name': v.name,
            'release_date': v.release_date.isoformat(),
            'is_active': v.is_active,
        }
        for v in versions
    ]
    return JsonResponse({'versions': data})

def api_dashboard(request):
    """JSON: агрегаты для дашборда + последние проблемы"""
    versions = ProductVersion.objects.all()

    version_stats = []
    for version in versions:
        stats = VisitSession.objects.filter(version=version).aggregate(
            total_visits=Count('id'),
            avg_duration=Avg('duration_sec'),
            bounce_rate=Avg(Cast('bounced', output_field=IntegerField())),
        )
        issue_count = UXIssue.objects.filter(version=version).count()
        critical_issues = UXIssue.objects.filter(version=version, severity='CRITICAL').count()

        version_stats.append({
            'id': version.id,
            'name': version.name,
            'release_date': version.release_date.isoformat(),
            'total_visits': stats['total_visits'] or 0,
            'avg_duration': round(stats['avg_duration'] or 0, 1),
            'bounce_rate': round((stats['bounce_rate'] or 0) * 100, 1),
            'issue_count': issue_count,
            'critical_issues': critical_issues,
        })

    recent_issues = UXIssue.objects.select_related('version').order_by('-created_at')[:5]
    recent_issues_list = []
    for issue in recent_issues:
        readable = get_readable_page_name(issue.location_url)
        recent_issues_list.append({
            'id': issue.id,
            'version': {'id': issue.version.id, 'name': issue.version.name},
            'severity': issue.severity,
            'issue_type': issue.issue_type,
            'description': issue.description,
            'location_url': issue.location_url,
            'readable_location': readable,
            'impact_score': issue.impact_score,
            'ai_hypothesis': issue.ai_hypothesis,
            'trend': issue.trend,
            'trend_label': get_trend_label(issue.trend),
            'priority': issue.priority,
            'recommended_specialists': issue.recommended_specialists,
            'detected_version_name': issue.detected_version_name or issue.version.name,
            'created_at': issue.created_at.isoformat(),
        })

    return JsonResponse({
        'version_stats': version_stats,
        'recent_issues': recent_issues_list,
    })

def api_compare(request):
    """JSON: сравнение двух версий"""
    v1_id = request.GET.get('v1')
    v2_id = request.GET.get('v2')
    versions = ProductVersion.objects.all().order_by('release_date')

    if not v1_id or not v2_id:
        if versions.count() >= 2:
            v1_id = versions[0].id
            v2_id = versions.last().id
        else:
            return JsonResponse({'error': 'Need at least two versions to compare'}, status=400)

    try:
        v1 = ProductVersion.objects.get(id=v1_id)
        v2 = ProductVersion.objects.get(id=v2_id)
    except ProductVersion.DoesNotExist:
        return JsonResponse({'error': 'Invalid version id'}, status=404)

    stats_v1 = VisitSession.objects.filter(version=v1).aggregate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        duration=Avg('duration_sec'),
    )
    stats_v2 = VisitSession.objects.filter(version=v2).aggregate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        duration=Avg('duration_sec'),
    )

    v1_visits = stats_v1['visits'] or 0
    v2_visits = stats_v2['visits'] or 0
    v1_bounce = (stats_v1['bounce'] or 0) * 100
    v2_bounce = (stats_v2['bounce'] or 0) * 100
    v1_dur = stats_v1['duration'] or 0
    v2_dur = stats_v2['duration'] or 0

    comparison = {
        'v1': {'id': v1.id, 'name': v1.name},
        'v2': {'id': v2.id, 'name': v2.name},
        'visits_diff': int(v2_visits - v1_visits),
        'bounce_diff': round(v2_bounce - v1_bounce, 1),
        'duration_diff': round(v2_dur - v1_dur, 1),
        'stats_v1': {'visits': v1_visits, 'bounce': round(v1_bounce, 1), 'duration': round(v1_dur, 1)},
        'stats_v2': {'visits': v2_visits, 'bounce': round(v2_bounce, 1), 'duration': round(v2_dur, 1)},
    }

    return JsonResponse({'comparison': comparison})

def api_issues(request):
    """JSON: список UX проблем с фильтрами"""
    version_id = request.GET.get('version')
    severity = request.GET.get('severity')
    issue_type = request.GET.get('issue_type')

    issues = UXIssue.objects.select_related('version').all().order_by('-impact_score', '-created_at')
    if version_id:
        issues = issues.filter(version_id=version_id)
    if severity:
        issues = issues.filter(severity=severity)
    if issue_type:
        issues = issues.filter(issue_type=issue_type)

    results = []
    for issue in issues:
        readable = get_readable_page_name(issue.location_url)
        results.append({
            'id': issue.id,
            'version': {'id': issue.version.id, 'name': issue.version.name},
            'issue_type': issue.issue_type,
            'severity': issue.severity,
            'description': issue.description,
            'location_url': issue.location_url,
            'readable_location': readable,
            'impact_score': issue.impact_score,
            'affected_sessions': issue.affected_sessions,
            'ai_hypothesis': issue.ai_hypothesis,
            'ai_solution': issue.ai_solution,
            'trend': issue.trend,
            'trend_label': get_trend_label(issue.trend),
            'priority': issue.priority,
            'recommended_specialists': issue.recommended_specialists,
            'detected_version_name': issue.detected_version_name or issue.version.name,
            'created_at': issue.created_at.isoformat(),
        })

    return JsonResponse({'count': len(results), 'results': results})

def api_daily_stats(request):
    """JSON: таймсерия по дням для графиков"""
    version_id = request.GET.get('version')
    if not version_id:
        return JsonResponse({'error': 'version parameter is required'}, status=400)

    stats = DailyStat.objects.filter(version_id=version_id).order_by('date')
    series = []
    for row in stats:
        bounce_rate = (row.total_bounces / row.total_sessions * 100) if row.total_sessions else 0
        series.append({
            'date': row.date.isoformat(),
            'total_sessions': row.total_sessions,
            'total_bounces': row.total_bounces,
            'bounce_rate': round(bounce_rate, 1),
            'avg_duration': round(row.avg_duration or 0, 1),
            'extra_data': row.extra_data,
        })

    return JsonResponse({'series': series})
