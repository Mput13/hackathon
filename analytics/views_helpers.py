import urllib.parse
import math
from django.db import models
from django.db.models import Avg, Count, IntegerField, Q
from django.db.models.functions import Cast
from .models import VisitSession, UXIssue, UserCohort, PageMetrics, PageHit
from .utils import get_readable_page_name


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


def _device_label(raw):
    """Нормализует значение device_category в человекочитаемый вид."""
    mapping = {
        '1': 'desktop', 1: 'desktop',
        '2': 'mobile', 2: 'mobile',
        '3': 'tablet', 3: 'tablet',
        '4': 'tv', 4: 'tv',
        'desktop': 'desktop',
        'mobile': 'mobile',
        'tablet': 'tablet',
        'tv': 'tv'
    }
    return mapping.get(raw, raw or 'unknown')


def _compute_paths(version_id, limit=20, min_count=5):
    """
    Возвращает топ путей (2-3 шага) для версии: path, steps, count, unique_users.
    """
    hits = PageHit.objects.filter(session__version_id=version_id).order_by(
        'session_id', 'timestamp'
    ).values(
        'session_id', 'url'
    )
    path_counts = {}
    path_sessions = {}
    current_session = None
    buffer = []

    def push_path(seq, session_key):
        if not seq or len(set(seq)) == 1:
            return
        path = tuple(seq)
        path_counts[path] = path_counts.get(path, 0) + 1
        if path not in path_sessions:
            path_sessions[path] = set()
        path_sessions[path].add(session_key)

    for row in hits:
        sid = row.get('session_id')
        if sid is None:
            continue
        if sid != current_session:
            buffer = []
            current_session = sid
        url_norm = _normalize_issue_url(row['url'])
        if not url_norm:
            continue
        # Пропускаем подряд дубли, чтобы не собирать шум вида A->A->B
        if buffer and buffer[-1] == url_norm:
            continue
        buffer.append(url_norm)
        if len(buffer) > 4:
            buffer = buffer[-4:]
        if len(buffer) >= 2:
            push_path(buffer[-2:], sid)
        if len(buffer) >= 3:
            push_path(buffer[-3:], sid)

    results = []
    for path, cnt in path_counts.items():
        if cnt < min_count:
            continue
        users = len(path_sessions.get(path, []))
        results.append({
            'path': " -> ".join(path),
            'steps': list(path),
            'count': cnt,
            'unique_users': users,
        })

    results = sorted(results, key=lambda x: x['count'], reverse=True)
    if limit > 0:
        results = results[:limit]
    return results


def _device_split_compare(v1, v2, stats_v1, stats_v2):
    """Возвращает сравнение по устройствам для двух версий."""
    dev_v1 = VisitSession.objects.filter(version=v1).values('device_category').annotate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        duration=Avg('duration_sec')
    )
    dev_v2 = VisitSession.objects.filter(version=v2).values('device_category').annotate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        duration=Avg('duration_sec')
    )
    total1 = stats_v1['visits'] or 0
    total2 = stats_v2['visits'] or 0
    dev_map = {}
    for row in dev_v1:
        key = _device_label(row['device_category'])
        dev_map[key] = {
            'device': key,
            'visits_v1': row['visits'],
            'share_v1': (row['visits'] / total1 * 100) if total1 else 0,
            'bounce_v1': (row['bounce'] or 0) * 100,
            'duration_v1': row['duration'] or 0
        }
    for row in dev_v2:
        key = _device_label(row['device_category'])
        if key not in dev_map:
            dev_map[key] = {'device': key, 'visits_v1': 0, 'share_v1': 0, 'bounce_v1': 0, 'duration_v1': 0}
        dev_map[key].update({
            'visits_v2': row['visits'],
            'share_v2': (row['visits'] / total2 * 100) if total2 else 0,
            'bounce_v2': (row['bounce'] or 0) * 100,
            'duration_v2': row['duration'] or 0
        })
    device_compare = []
    for val in dev_map.values():
        device_compare.append({
            'device': val['device'],
            'visits_v1': val.get('visits_v1', 0),
            'visits_v2': val.get('visits_v2', 0),
            'share_v1': round(val.get('share_v1', 0), 2),
            'share_v2': round(val.get('share_v2', 0), 2),
            'share_diff': round(val.get('share_v2', 0) - val.get('share_v1', 0), 2),
            'bounce_v1': round(val.get('bounce_v1', 0), 1),
            'bounce_v2': round(val.get('bounce_v2', 0), 1),
            'bounce_diff': round(val.get('bounce_v2', 0) - val.get('bounce_v1', 0), 1),
            'duration_v1': round(val.get('duration_v1', 0), 1),
            'duration_v2': round(val.get('duration_v2', 0), 1),
            'duration_diff': round(val.get('duration_v2', 0) - val.get('duration_v1', 0), 1),
        })
    return device_compare


def _agent_split_compare(v1, v2, stats_v1, stats_v2, field):
    """Сравнение по браузерам/OS (field='browser' или 'os') с дельтами (топ-5 по трафику)."""
    qs1 = VisitSession.objects.filter(version=v1).values(field).annotate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        duration=Avg('duration_sec')
    ).order_by('-visits')[:5]
    qs2 = VisitSession.objects.filter(version=v2).values(field).annotate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        duration=Avg('duration_sec')
    ).order_by('-visits')[:5]
    total1 = stats_v1['visits'] or 0
    total2 = stats_v2['visits'] or 0
    mp = {}
    for row in qs1:
        key = row[field] or 'unknown'
        mp[key] = {
            field: key,
            'visits_v1': row['visits'],
            'share_v1': (row['visits'] / total1 * 100) if total1 else 0,
            'bounce_v1': (row['bounce'] or 0) * 100,
            'duration_v1': row['duration'] or 0
        }
    for row in qs2:
        key = row[field] or 'unknown'
        if key not in mp:
            mp[key] = {field: key, 'visits_v1': 0, 'share_v1': 0, 'bounce_v1': 0, 'duration_v1': 0}
        mp[key].update({
            'visits_v2': row['visits'],
            'share_v2': (row['visits'] / total2 * 100) if total2 else 0,
            'bounce_v2': (row['bounce'] or 0) * 100,
            'duration_v2': row['duration'] or 0
        })
    res = []
    for val in mp.values():
        res.append({
            field: val[field],
            'visits_v1': val.get('visits_v1', 0),
            'visits_v2': val.get('visits_v2', 0),
            'share_v1': round(val.get('share_v1', 0), 2),
            'share_v2': round(val.get('share_v2', 0), 2),
            'share_diff': round(val.get('share_v2', 0) - val.get('share_v1', 0), 2),
            'bounce_v1': round(val.get('bounce_v1', 0), 1),
            'bounce_v2': round(val.get('bounce_v2', 0), 1),
            'bounce_diff': round(val.get('bounce_v2', 0) - val.get('bounce_v1', 0), 1),
            'duration_v1': round(val.get('duration_v1', 0), 1),
            'duration_v2': round(val.get('duration_v2', 0), 1),
            'duration_diff': round(val.get('duration_v2', 0) - val.get('duration_v1', 0), 1),
        })
    return res


def _build_alerts_dashboard(version):
    """
    Простейшие алерты: новые CRITICAL issues и страницы с высоким exit/bounce.
    """
    alerts = []
    # Новые/свежие CRITICAL issues
    critical_issues = UXIssue.objects.filter(version=version, severity='CRITICAL').order_by('-created_at')[:10]
    for issue in critical_issues:
        alerts.append({
            'type': 'CRITICAL_ISSUE',
            'message': issue.description,
            'location': get_readable_page_name(issue.location_url),
            'url': issue.location_url,
            'issue_id': issue.id,
            'severity': 'critical',
        })

    # Страницы с высоким exit/bounce
    risky_pages = PageMetrics.objects.filter(
        version=version,
        total_views__gte=100
    ).filter(models.Q(exit_rate__gt=70) | models.Q(bounce_rate__gt=70)).order_by('-exit_rate')[:10]
    for page in risky_pages:
        alerts.append({
            'type': 'HIGH_EXIT',
            'message': f"Высокий выход/отказ на {get_readable_page_name(page.url)}",
            'url': page.url,
            'exit_rate': page.exit_rate,
            'bounce_rate': page.bounce_rate,
            'severity': 'warning' if page.exit_rate < 80 else 'critical'
        })
    return alerts


def _build_alerts_compare(issues_diff, pages_diff):
    """
    Алерты для сравнения: новые критические и рост exit.
    """
    alerts = []
    for row in issues_diff:
        issue = row['issue']
        if row['status'] == 'new' and issue.severity == 'CRITICAL':
            alerts.append({
                'type': 'NEW_CRITICAL',
                'message': issue.description,
                'url': issue.location_url,
                'issue_id': issue.id,
                'severity': 'critical'
            })
    for row in pages_diff:
        if row['status'] == 'changed' and row['exit_diff'] > 10:
            alerts.append({
                'type': 'EXIT_INCREASE',
                'message': f"Рост выхода на {row['exit_diff']} п.п. для {row['readable']}",
                'url': row['v2'].url if row['v2'] else (row['v1'].url if row['v1'] else ''),
                'severity': 'warning' if row['exit_diff'] < 20 else 'critical'
            })
    return alerts


def _build_comparison(v1, v2):
    """
    Подготовка структуры сравнения для UI и API, чтобы не дублировать логику.
    """
    stats_v1 = VisitSession.objects.filter(version=v1).aggregate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        bounce_count=Count('id', filter=Q(bounced=True)),
        duration=Avg('duration_sec')
    )
    stats_v2 = VisitSession.objects.filter(version=v2).aggregate(
        visits=Count('id'),
        bounce=Avg(Cast('bounced', output_field=IntegerField())),
        bounce_count=Count('id', filter=Q(bounced=True)),
        duration=Avg('duration_sec')
    )

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

    pages_v1 = {_normalize_issue_url(m.url): m for m in PageMetrics.objects.filter(version=v1)}
    pages_v2 = {_normalize_issue_url(m.url): m for m in PageMetrics.objects.filter(version=v2)}
    page_diff = []
    keys = set(pages_v1.keys()) | set(pages_v2.keys())
    for key in keys:
        m1 = pages_v1.get(key)
        m2 = pages_v2.get(key)
        views1 = m1.total_views if m1 else 0
        views2 = m2.total_views if m2 else 0
        max_views = max(views1, views2)
        if max_views and max_views < 20:
            continue
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

    def _proportion_pvalue(count1, total1, count2, total2):
        """Простой z-test для долей, без внешних зависимостей."""
        if not total1 or not total2:
            return None
        p1 = count1 / total1
        p2 = count2 / total2
        p_pool = (count1 + count2) / (total1 + total2)
        se = math.sqrt(max(p_pool * (1 - p_pool) * (1 / total1 + 1 / total2), 0.0000001))
        if se == 0:
            return None
        z = (p2 - p1) / se
        # двусторонний p-value через erfc
        return round(2 * (0.5 * math.erfc(abs(z) / math.sqrt(2))), 6)

    bounce_pvalue = _proportion_pvalue(
        stats_v1.get('bounce_count') or 0,
        v1_visits,
        stats_v2.get('bounce_count') or 0,
        v2_visits
    )

    return {
        'v1': v1, 'v2': v2,
        'visits_diff': int(v2_visits - v1_visits),
        'bounce_diff': round(v2_bounce - v1_bounce, 1),
        'duration_diff': round(v2_dur - v1_dur, 1),
        'bounce_pvalue': bounce_pvalue,
        'stats_v1': {'visits': v1_visits, 'bounce': round(v1_bounce, 1), 'duration': round(v1_dur, 1)},
        'stats_v2': {'visits': v2_visits, 'bounce': round(v2_bounce, 1), 'duration': round(v2_dur, 1)},
        'v1_cohorts': v1_cohorts,
        'v2_cohorts': v2_cohorts,
        'issues_diff': issues_diff[:20],
        'pages_diff': page_diff[:20],
        'cohorts_diff': cohorts_diff[:20],
    }


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


__all__ = [
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
]
