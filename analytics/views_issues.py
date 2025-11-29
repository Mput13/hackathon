from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Avg, IntegerField
from django.db.models.functions import Cast
from .models import ProductVersion, UXIssue, DailyStat
from .utils import get_readable_page_name
from .views_helpers import get_trend_label


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


__all__ = ['issues_list', 'api_versions', 'api_issues', 'api_daily_stats']
