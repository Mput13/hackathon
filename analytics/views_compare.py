from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Count, IntegerField
from django.db.models.functions import Cast
from .models import ProductVersion, VisitSession
from .views_helpers import (
    _build_comparison,
    _device_split_compare,
    _agent_split_compare,
    _compute_paths,
    _build_alerts_compare,
)
from .ai_service import analyze_version_comparison_with_ai
from django.db.models import Avg, Count, IntegerField
from django.db.models.functions import Cast
from .ai_service import analyze_version_comparison_with_ai


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
            v1_id = ordered_versions[0].id  # Oldest
            v2_id = ordered_versions[ordered_versions.count() - 1].id  # Newest

    context = {
        'versions': all_versions,
        'selected_v1': int(v1_id) if v1_id else None,
        'selected_v2': int(v2_id) if v2_id else None,
    }

    if v1_id and v2_id:
        try:
            v1 = ProductVersion.objects.get(id=v1_id)
            v2 = ProductVersion.objects.get(id=v2_id)
            comparison = _build_comparison(v1, v2)
            stats_v1 = {'visits': comparison['stats_v1']['visits']}
            stats_v2 = {'visits': comparison['stats_v2']['visits']}
            comparison['device_split'] = _device_split_compare(v1, v2, stats_v1, stats_v2)
            comparison['browser_split'] = _agent_split_compare(v1, v2, stats_v1, stats_v2, 'browser')
            comparison['os_split'] = _agent_split_compare(v1, v2, stats_v1, stats_v2, 'os')
            comparison['paths_v1'] = _compute_paths(v1.id, limit=10, min_count=5)
            comparison['paths_v2'] = _compute_paths(v2.id, limit=10, min_count=5)
            comparison['alerts'] = _build_alerts_compare(comparison['issues_diff'], comparison['pages_diff'])
            
            # Инициализируем ai_analysis как None по умолчанию
            comparison['ai_analysis'] = None
            
            # Генерируем AI-анализ
            try:
                stats_v1_for_ai = VisitSession.objects.filter(version=v1).aggregate(
                    visits=Count('id'),
                    bounce=Avg(Cast('bounced', output_field=IntegerField())),
                    duration=Avg('duration_sec'),
                )
                stats_v2_for_ai = VisitSession.objects.filter(version=v2).aggregate(
                    visits=Count('id'),
                    bounce=Avg(Cast('bounced', output_field=IntegerField())),
                    duration=Avg('duration_sec'),
                )
                
                ai_result = analyze_version_comparison_with_ai(
                    v1_name=v1.name,
                    v2_name=v2.name,
                    stats_v1=stats_v1_for_ai,
                    stats_v2=stats_v2_for_ai,
                    issues_diff=comparison['issues_diff'],
                    pages_diff=comparison['pages_diff'],
                    cohorts_diff=comparison.get('cohorts_diff', []),
                    alerts=comparison['alerts']
                )
                # Убеждаемся, что результат не пустой
                # Функция всегда должна возвращать строку (либо от AI, либо fallback)
                if ai_result and ai_result.strip():
                    comparison['ai_analysis'] = ai_result.strip()
                else:
                    # Если даже fallback не сработал, используем базовое сообщение
                    comparison['ai_analysis'] = "Резюме: Недостаточно данных для анализа. Улучшения: требуется больше данных. Проблемы: требуется больше данных. Рекомендация: собрать больше данных для сравнения версий."
            except Exception as e:
                # Если AI недоступен - просто не добавляем анализ
                import traceback
                print(f"AI analysis error in compare_versions: {e}")
                print(traceback.format_exc())
                comparison['ai_analysis'] = None
            
            # Убеждаемся, что ai_analysis всегда установлен
            if 'ai_analysis' not in comparison:
                comparison['ai_analysis'] = None
            
            context['comparison'] = comparison
        except ProductVersion.DoesNotExist:
            pass  # Just don't show comparison if IDs are invalid

    return render(request, 'analytics/compare.html', context)


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

    v1_bounce = (stats_v1['bounce'] or 0) * 100
    v2_bounce = (stats_v2['bounce'] or 0) * 100
    comparison = _build_comparison(v1, v2)
    device_compare = _device_split_compare(v1, v2, stats_v1, stats_v2)
    browser_compare = _agent_split_compare(v1, v2, stats_v1, stats_v2, 'browser')
    os_compare = _agent_split_compare(v1, v2, stats_v1, stats_v2, 'os')
    alerts = _build_alerts_compare(comparison['issues_diff'], comparison['pages_diff'])

    # Приводим к JSON-сериализуемому виду
    def serialize_cohort(c):
        return {
            'name': c.name,
            'percentage': c.display_percentage if hasattr(c, 'display_percentage') else (c.percentage or 0) * 100,
            'avg_bounce_rate': c.avg_bounce_rate,
            'avg_duration': c.avg_duration,
            'users_count': c.users_count,
            'metrics': c.metrics,
            'conversion_rates': c.conversion_rates,
        }

    def serialize_issue_row(row):
        issue = row['issue']
        return {
            'id': issue.id,
            'issue_type': issue.issue_type,
            'severity': issue.severity,
            'location_url': issue.location_url,
            'location_readable': row['location_readable'],
            'impact_score': issue.impact_score,
            'affected_sessions': issue.affected_sessions,
            'status': row['status'],
            'impact_diff': row['impact_diff'],
            'trend': issue.trend,
            'priority': issue.priority,
            'recommended_specialists': issue.recommended_specialists,
            'detected_version_name': issue.detected_version_name or issue.version.name,
        }

    def serialize_page_row(row):
        def pack(m):
            if not m:
                return None
            return {
                'url': m.url,
                'page_title': m.page_title,
                'exit_rate': m.exit_rate,
                'avg_time_on_page': m.avg_time_on_page,
                'avg_scroll_depth': m.avg_scroll_depth,
                'total_views': m.total_views,
                'unique_visitors': m.unique_visitors,
                'dominant_cohort': m.dominant_cohort,
                'dominant_device': m.dominant_device,
            }
        return {
            'status': row['status'],
            'exit_diff': row['exit_diff'],
            'time_diff': row['time_diff'],
            'readable': row['readable'],
            'v1': pack(row['v1']),
            'v2': pack(row['v2']),
        }

    def serialize_cohort_row(row):
        return {
            'name': row['name'],
            'status': row['status'],
            'v1': serialize_cohort(row['v1']) if row['v1'] else None,
            'v2': serialize_cohort(row['v2']) if row['v2'] else None,
        }

    # Генерируем AI-анализ сравнения
    ai_analysis = None
    try:
        # Подготавливаем данные для AI
        stats_v1_for_ai = {
            'visits': stats_v1['visits'] or 0,
            'bounce': stats_v1['bounce'] or 0,
            'duration': stats_v1['duration'] or 0,
        }
        stats_v2_for_ai = {
            'visits': stats_v2['visits'] or 0,
            'bounce': stats_v2['bounce'] or 0,
            'duration': stats_v2['duration'] or 0,
        }
        
        ai_analysis = analyze_version_comparison_with_ai(
            v1_name=v1.name,
            v2_name=v2.name,
            stats_v1=stats_v1_for_ai,
            stats_v2=stats_v2_for_ai,
            issues_diff=comparison['issues_diff'],
            pages_diff=comparison['pages_diff'],
            cohorts_diff=comparison.get('cohorts_diff', []),
            alerts=alerts
        )
    except Exception as e:
        # Если AI недоступен или ошибка - просто не добавляем анализ
        import traceback
        print(f"AI analysis error: {e}")
        print(traceback.format_exc())
        ai_analysis = None

    data = {
        'v1': {'id': v1.id, 'name': v1.name},
        'v2': {'id': v2.id, 'name': v2.name},
        'visits_diff': comparison['visits_diff'],
        'bounce_diff': comparison['bounce_diff'],
        'duration_diff': comparison['duration_diff'],
        'stats_v1': {
            'visits': stats_v1['visits'] or 0,
            'bounce': round(v1_bounce, 1),
            'duration': round(stats_v1['duration'] or 0, 1),
        },
        'stats_v2': {
            'visits': stats_v2['visits'] or 0,
            'bounce': round(v2_bounce, 1),
            'duration': round(stats_v2['duration'] or 0, 1),
        },
        'v1_cohorts': [serialize_cohort(c) for c in comparison['v1_cohorts']],
        'v2_cohorts': [serialize_cohort(c) for c in comparison['v2_cohorts']],
        'issues_diff': [serialize_issue_row(r) for r in comparison['issues_diff']],
        'pages_diff': [serialize_page_row(r) for r in comparison['pages_diff']],
        'cohorts_diff': [serialize_cohort_row(r) for r in comparison['cohorts_diff']],
        'device_split': device_compare,
        'browser_split': browser_compare,
        'os_split': os_compare,
        'alerts': alerts,
        'ai_analysis': ai_analysis,  # Добавляем AI-анализ
    }

    return JsonResponse({'comparison': data})


__all__ = ['compare_versions', 'api_compare']
