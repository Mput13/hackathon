from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('compare/', views.compare_versions, name='compare'),
    path('issues/', views.issues_list, name='issues_list'),
    path('funnels/', views.funnels_list, name='funnels_list'),
    path('funnels/<int:funnel_id>/', views.funnel_detail, name='funnel_detail'),
    # JSON API endpoints for frontend
    path('api/versions/', views.api_versions, name='api_versions'),
    path('api/dashboard/', views.api_dashboard, name='api_dashboard'),
    path('api/compare/', views.api_compare, name='api_compare'),
    path('api/issues/', views.api_issues, name='api_issues'),
    path('api/daily-stats/', views.api_daily_stats, name='api_daily_stats'),
    # Funnel API endpoints
    path('api/funnels/', views.api_funnels, name='api_funnels'),
    path('api/funnels/<int:funnel_id>/', views.api_funnel_detail, name='api_funnel_detail'),
    path('api/funnels/<int:funnel_id>/by-cohorts/', views.api_funnel_by_cohorts, name='api_funnel_by_cohorts'),
]
