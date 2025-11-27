from django.shortcuts import render
from django.db.models import Sum, Avg, Count
from .models import ProductVersion, VisitSession, UXIssue, DailyStat
from .utils import get_readable_page_name

def dashboard(request):
    """Main Dashboard View"""
    versions = ProductVersion.objects.all()
    
    # Get stats for each version
    version_stats = []
    for version in versions:
        stats = VisitSession.objects.filter(version=version).aggregate(
            total_visits=Count('id'),
            avg_duration=Avg('duration_sec'),
            bounce_rate=Avg('bounced') # Casts boolean to int 0/1, avg gives rate
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
    recent_issues = UXIssue.objects.select_related('version').order_by('-created_at')[:5]
    for issue in recent_issues:
        issue.readable_location = get_readable_page_name(issue.location_url)

    context = {
        'version_stats': version_stats,
        'recent_issues': recent_issues
    }
    return render(request, 'analytics/dashboard.html', context)

def compare_versions(request):
    """Compare View (v1 vs v2)"""
    v1_id = request.GET.get('v1')
    v2_id = request.GET.get('v2')
    
    if not v1_id or not v2_id:
        # Default to first two versions if available
        versions = ProductVersion.objects.all()[:2]
        if len(versions) == 2:
            v1_id = versions[0].id
            v2_id = versions[1].id
    
    context = {'versions': ProductVersion.objects.all()}
    
    if v1_id and v2_id:
        v1 = ProductVersion.objects.get(id=v1_id)
        v2 = ProductVersion.objects.get(id=v2_id)
        
        stats_v1 = VisitSession.objects.filter(version=v1).aggregate(
            visits=Count('id'),
            bounce=Avg('bounced'),
            duration=Avg('duration_sec')
        )
        
        stats_v2 = VisitSession.objects.filter(version=v2).aggregate(
            visits=Count('id'),
            bounce=Avg('bounced'),
            duration=Avg('duration_sec')
        )
        
        # Calculate Diff
        comparison = {
            'v1': v1, 'v2': v2,
            'visits_diff': (stats_v2['visits'] or 0) - (stats_v1['visits'] or 0),
            'bounce_diff': round(((stats_v2['bounce'] or 0) - (stats_v1['bounce'] or 0)) * 100, 1),
            'duration_diff': round((stats_v2['duration'] or 0) - (stats_v1['duration'] or 0), 1),
            'stats_v1': stats_v1,
            'stats_v2': stats_v2
        }
        context['comparison'] = comparison
        
    return render(request, 'analytics/compare.html', context)
