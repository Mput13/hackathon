from django.shortcuts import render
from django.db.models import Avg, Count, IntegerField
from django.db.models.functions import Cast
from .models import ProductVersion, VisitSession, UXIssue
from .utils import get_readable_page_name
from .views_helpers import (
    _device_label,
    _build_alerts_dashboard,
    get_trend_label,
)


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

        # Device split
        by_device = VisitSession.objects.filter(version=version).values('device_category').annotate(
            visits=Count('id'),
            bounce=Avg(Cast('bounced', output_field=IntegerField())),
            duration=Avg('duration_sec')
        )
        total_visits = stats['total_visits'] or 0
        devices = []
        for row in by_device:
            share = (row['visits'] / total_visits * 100) if total_visits else 0
            dev_label = _device_label(row['device_category'])
            devices.append({
                'device': dev_label,
                'visits': row['visits'],
                'share': round(share, 2),
                'bounce_rate': round((row['bounce'] or 0) * 100, 1),
                'avg_duration': round(row['duration'] or 0, 1)
            })

        # Browser split (top-5)
        by_browser = VisitSession.objects.filter(version=version).values('browser').annotate(
            visits=Count('id'),
            bounce=Avg(Cast('bounced', output_field=IntegerField())),
            duration=Avg('duration_sec')
        ).order_by('-visits')[:5]
        browsers = []
        for row in by_browser:
            share = (row['visits'] / total_visits * 100) if total_visits else 0
            browsers.append({
                'browser': row['browser'] or 'unknown',
                'visits': row['visits'],
                'share': round(share, 2),
                'bounce_rate': round((row['bounce'] or 0) * 100, 1),
                'avg_duration': round(row['duration'] or 0, 1)
            })

        alerts = _build_alerts_dashboard(version)

        version_stats.append({
            'version': version,
            'total_visits': stats['total_visits'] or 0,
            'avg_duration': round(stats['avg_duration'] or 0, 1),
            'bounce_rate': round((stats['bounce_rate'] or 0) * 100, 1),
            'issue_count': issue_count,
            'critical_issues': critical_issues,
            'device_split': devices,
            'browser_split': browsers,
            'alerts': alerts
        })

    # Get recent issues for the dashboard list
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

        # Разрез по устройствам
        by_device = VisitSession.objects.filter(version=version).values('device_category').annotate(
            visits=Count('id'),
            bounce=Avg(Cast('bounced', output_field=IntegerField())),
            duration=Avg('duration_sec')
        )
        total_visits = stats['total_visits'] or 0
        devices = []
        for row in by_device:
            share = (row['visits'] / total_visits * 100) if total_visits else 0
            dev_label = _device_label(row['device_category'])
            devices.append({
                'device': dev_label,
                'visits': row['visits'],
                'share': round(share, 2),
                'bounce_rate': round((row['bounce'] or 0) * 100, 1),
                'avg_duration': round(row['duration'] or 0, 1)
            })

        # Разрез по браузерам (топ-5)
        by_browser = VisitSession.objects.filter(version=version).values('browser').annotate(
            visits=Count('id'),
            bounce=Avg(Cast('bounced', output_field=IntegerField())),
            duration=Avg('duration_sec')
        ).order_by('-visits')[:5]
        browsers = []
        for row in by_browser:
            share = (row['visits'] / total_visits * 100) if total_visits else 0
            browsers.append({
                'browser': row['browser'] or 'unknown',
                'visits': row['visits'],
                'share': round(share, 2),
                'bounce_rate': round((row['bounce'] or 0) * 100, 1),
                'avg_duration': round(row['duration'] or 0, 1)
            })

        version_stats.append({
            'id': version.id,
            'name': version.name,
            'release_date': version.release_date.isoformat(),
            'total_visits': stats['total_visits'] or 0,
            'avg_duration': round(stats['avg_duration'] or 0, 1),
            'bounce_rate': round((stats['bounce_rate'] or 0) * 100, 1),
            'issue_count': issue_count,
            'critical_issues': critical_issues,
            'device_split': devices,
            'browser_split': browsers,
            'alerts': _build_alerts_dashboard(version),
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

    from django.http import JsonResponse
    return JsonResponse({
        'version_stats': version_stats,
        'recent_issues': recent_issues_list,
    })


__all__ = ['dashboard', 'api_dashboard']
