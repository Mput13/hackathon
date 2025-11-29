import os
from django.conf import settings
from django.http import JsonResponse
from .models import UserCohort, PageMetrics, UXIssue
from .utils import get_readable_page_name, GoalParser
from .views_helpers import _normalize_issue_url, _compute_paths


def api_cohorts(request):
    """JSON: список когорт по версии"""
    version_id = request.GET.get('version')
    if not version_id:
        return JsonResponse({'error': 'version parameter is required'}, status=400)

    cohorts = UserCohort.objects.filter(version_id=version_id).order_by('-percentage')
    data = []
    for c in cohorts:
        data.append({
            'id': c.id,
            'name': c.name,
            'percentage': round((c.percentage or 0) * 100, 2),
            'users_count': c.users_count,
            'avg_bounce_rate': c.avg_bounce_rate,
            'avg_duration': c.avg_duration,
            'avg_depth': c.metrics.get('depth') if isinstance(c.metrics, dict) else None,
            'metrics': c.metrics,
            'conversion_rates': c.conversion_rates,
        })
    return JsonResponse({'count': len(data), 'results': data})


def api_pages(request):
    """JSON: метрики по страницам для выбранной версии"""
    version_id = request.GET.get('version')
    if not version_id:
        return JsonResponse({'error': 'version parameter is required'}, status=400)

    try:
        limit = int(request.GET.get('limit', 50))
    except ValueError:
        limit = 50
    try:
        min_views = int(request.GET.get('min_views', 0))
    except ValueError:
        min_views = 0

    order = request.GET.get('order', '-exit_rate')
    allowed_order = ['exit_rate', '-exit_rate', 'avg_time_on_page', '-avg_time_on_page', 'total_views', '-total_views']
    if order not in allowed_order:
        order = '-exit_rate'

    qs = PageMetrics.objects.filter(version_id=version_id)
    if min_views > 0:
        qs = qs.filter(total_views__gte=min_views)
    qs = qs.order_by(order)
    if limit > 0:
        qs = qs[:limit]

    data = []
    for m in qs:
        norm_url = _normalize_issue_url(m.url)
        data.append({
            'url': m.url,
            'norm_url': norm_url,
            'readable': get_readable_page_name(m.url),
            'page_title': m.page_title,
            'total_views': m.total_views,
            'unique_visitors': m.unique_visitors,
            'avg_time_on_page': m.avg_time_on_page,
            'bounce_rate': m.bounce_rate,
            'exit_rate': m.exit_rate,
            'avg_scroll_depth': m.avg_scroll_depth,
            'dominant_cohort': m.dominant_cohort,
            'dominant_device': m.dominant_device,
        })
    return JsonResponse({'count': len(data), 'results': data})


def api_paths(request):
    """JSON: топ пользовательских путей (2-3 шага) для версии."""
    version_id = request.GET.get('version')
    if not version_id:
        return JsonResponse({'error': 'version parameter is required'}, status=400)
    try:
        limit = int(request.GET.get('limit', 20))
    except ValueError:
        limit = 20
    try:
        min_count = int(request.GET.get('min_count', 5))
    except ValueError:
        min_count = 5
    results = _compute_paths(version_id, limit=limit, min_count=min_count)

    return JsonResponse({'count': len(results), 'results': results})


def api_issue_history(request):
    """
    JSON: История/жизненный цикл проблем.
    Группируем по (issue_type, norm_url) и отдаём список наблюдений по версиям/датам.
    """
    issue_type = request.GET.get('issue_type')
    norm_url_filter = request.GET.get('norm_url')

    qs = UXIssue.objects.select_related('version').order_by('created_at')
    if issue_type:
        qs = qs.filter(issue_type=issue_type)

    grouped = {}
    for issue in qs:
        norm_url = _normalize_issue_url(issue.location_url)
        if norm_url_filter and norm_url != norm_url_filter:
            continue
        key = (issue.issue_type, norm_url)
        if key not in grouped:
            grouped[key] = {
                'issue_type': issue.issue_type,
                'norm_url': norm_url,
                'readable_location': get_readable_page_name(issue.location_url),
                'observations': []
            }
        grouped[key]['observations'].append({
            'version': {'id': issue.version.id, 'name': issue.version.name},
            'severity': issue.severity,
            'impact_score': issue.impact_score,
            'affected_sessions': issue.affected_sessions,
            'trend': issue.trend,
            'priority': issue.priority,
            'created_at': issue.created_at.isoformat(),
        })

    results = []
    for val in grouped.values():
        val['observations'] = sorted(val['observations'], key=lambda x: x['created_at'])
        results.append(val)

    return JsonResponse({'count': len(results), 'results': results})

def api_goals(request):
    """JSON: список целей из goals.yaml"""
    default_path = os.path.join(getattr(settings, 'BASE_DIR', ''), 'analytics', 'goals.yaml')
    parser = GoalParser(config_path=default_path if os.path.exists(default_path) else 'goals.yaml')
    goals = parser.get_goals() or []
    return JsonResponse({'count': len(goals), 'results': goals})


__all__ = ['api_cohorts', 'api_pages', 'api_paths', 'api_issue_history', 'api_goals']
