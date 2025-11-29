from .views_helpers import (
    _normalize_issue_url,
    _device_label,
    _compute_paths,
    _device_split_compare,
    _agent_split_compare,
    _build_alerts_dashboard,
    _build_alerts_compare,
    _build_comparison,
    TREND_LABELS,
    get_trend_label,
)
from .views_dashboard import dashboard, api_dashboard
from .views_compare import compare_versions, api_compare
from .views_issues import issues_list, api_versions, api_issues, api_daily_stats
from .views_api_extra import api_cohorts, api_pages, api_paths, api_issue_history, api_goals
from .views_funnels import (
    funnels_list, 
    funnel_detail, 
    funnel_create,
    funnel_edit,
    funnel_delete,
    api_funnels, 
    api_funnel_detail, 
    api_funnel_by_cohorts
)

__all__ = [
    # helpers
    "_normalize_issue_url",
    "_device_label",
    "_compute_paths",
    "_device_split_compare",
    "_agent_split_compare",
    "_build_alerts_dashboard",
    "_build_alerts_compare",
    "_build_comparison",
    "TREND_LABELS",
    "get_trend_label",
    # views
    "dashboard",
    "api_dashboard",
    "compare_versions",
    "api_compare",
    "issues_list",
    "api_versions",
    "api_issues",
    "api_daily_stats",
    "api_cohorts",
    "api_pages",
    "api_paths",
    "api_issue_history",
    "api_goals",
    "funnels_list",
    "funnel_detail",
    "funnel_create",
    "funnel_edit",
    "funnel_delete",
    "api_funnels",
    "api_funnel_detail",
    "api_funnel_by_cohorts",
]
