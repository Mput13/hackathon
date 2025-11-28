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
    # Fallback to empty list if no issues found
    recent_issues = UXIssue.objects.select_related('version').order_by('-created_at')[:5]
    
    # Convert QuerySet to list to allow modifying attributes
    recent_issues_list = []
    for issue in recent_issues:
        issue.readable_location = get_readable_page_name(issue.location_url)
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
                bounce=Avg('bounced'),
                duration=Avg('duration_sec')
            )
            
            stats_v2 = VisitSession.objects.filter(version=v2).aggregate(
                visits=Count('id'),
                bounce=Avg('bounced'),
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
            
            comparison = {
                'v1': v1, 'v2': v2,
                'visits_diff': int(v2_visits - v1_visits),
                'bounce_diff': round(v2_bounce - v1_bounce, 1),
                'duration_diff': round(v2_dur - v1_dur, 1),
                'stats_v1': {'visits': v1_visits, 'bounce': round(v1_bounce, 1), 'duration': round(v1_dur, 1)},
                'stats_v2': {'visits': v2_visits, 'bounce': round(v2_bounce, 1), 'duration': round(v2_dur, 1)}
            }
            context['comparison'] = comparison
        except ProductVersion.DoesNotExist:
            pass # Just don't show comparison if IDs are invalid
        
    return render(request, 'analytics/compare.html', context)
