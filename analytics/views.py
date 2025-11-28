from django.shortcuts import render
from django.db.models import Sum, Avg, Count, Case, When, IntegerField
from django.db.models.functions import Cast
from django.http import JsonResponse
from .models import ProductVersion, VisitSession, UXIssue, DailyStat, UserCohort
from .utils import get_readable_page_name

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
            # Handle None values safely
            v1_visits = stats_v1['visits'] or 0
            v2_visits = stats_v2['visits'] or 0
            
            v1_bounce = (stats_v1['bounce'] or 0) * 100
            v2_bounce = (stats_v2['bounce'] or 0) * 100
            
            v1_dur = stats_v1['duration'] or 0
            v2_dur = stats_v2['duration'] or 0

            v1_cohorts = UserCohort.objects.filter(version=v1).order_by('-percentage')
            v2_cohorts = UserCohort.objects.filter(version=v2).order_by('-percentage')
            
            comparison = {
                'v1': v1, 'v2': v2,
                'visits_diff': int(v2_visits - v1_visits),
                'bounce_diff': round(v2_bounce - v1_bounce, 1),
                'duration_diff': round(v2_dur - v1_dur, 1),
                'stats_v1': {'visits': v1_visits, 'bounce': round(v1_bounce, 1), 'duration': round(v1_dur, 1)},
                'stats_v2': {'visits': v2_visits, 'bounce': round(v2_bounce, 1), 'duration': round(v2_dur, 1)},
                'v1_cohorts': v1_cohorts,
                'v2_cohorts': v2_cohorts
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
