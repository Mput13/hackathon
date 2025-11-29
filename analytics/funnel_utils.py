"""
Утилиты для расчета метрик воронок конверсии
Оптимизировано для работы с БД, минимальное использование памяти
"""
from django.db.models import Count, Q, Exists, OuterRef
from django.db import connection
from analytics.models import ConversionFunnel, VisitSession, PageHit, UserCohort
from analytics.utils import GoalParser
import urllib.parse
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict


def normalize_url(url: str) -> str:
    """Нормализация URL (аналогично _normalize_issue_url из views.py)"""
    if not isinstance(url, str):
        return ""
    parsed = urllib.parse.urlparse(url.strip())
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


def matches_funnel_step(hit: PageHit, step_config: Dict[str, Any], goal_parser: GoalParser) -> bool:
    """
    Проверяет, соответствует ли hit шагу воронки
    
    Args:
        hit: PageHit объект
        step_config: Конфигурация шага {'type': 'goal'|'url', 'code'|'url': ..., 'name': ...}
        goal_parser: Парсер целей для проверки goal-шагов
    
    Returns:
        bool: True если hit соответствует шагу
    """
    step_type = step_config.get('type')
    
    if step_type == 'goal':
        goal_code = step_config.get('code')
        if not goal_code:
            return False
        
        goal_config = goal_parser.get_goal_by_code(goal_code)
        if not goal_config:
            return False
        
        match_type = goal_config['match']['type']
        match_value = goal_config['match'].get('value')
        
        if match_type == 'identifier':
            # Identifier goals проверяются через goalsID в сессии, не через hits
            return False
        
        elif match_type == 'url_prefix':
            return hit.url.startswith(match_value) if match_value else False
        
        elif match_type == 'url_contains':
            return match_value in hit.url if match_value else False
        
        elif match_type == 'click':
            # Click goals требуют специальной обработки
            return False
    
    elif step_type == 'url':
        target_url = step_config.get('url', '')
        if not target_url or not hit.url:
            return False
        
        # Нормализуем URL (убираем параметры для сравнения базового пути)
        normalized_hit_url = normalize_url(hit.url)
        normalized_target_url = normalize_url(target_url)
        
        # Точное совпадение после нормализации
        if normalized_hit_url == normalized_target_url:
            return True
        
        # Извлекаем пути без протокола и домена
        def extract_path(url):
            url_normalized = normalize_url(url)
            for domain in ['https://priem.mai.ru', 'http://priem.mai.ru', 'https://mai.ru', 'http://mai.ru']:
                url_normalized = url_normalized.replace(domain, '')
            # Убираем параметры запроса для сравнения базового пути
            if '?' in url_normalized:
                url_normalized = url_normalized.split('?')[0]
            return url_normalized.rstrip('/')
        
        hit_path = extract_path(hit.url)
        target_path = extract_path(target_url)
        
        # Нормализуем пути: /bachelor/ и /base/ считаются эквивалентными
        hit_path_normalized = hit_path.replace('/base/', '/bachelor/')
        target_path_normalized = target_path.replace('/base/', '/bachelor/')
        
        # Проверяем, начинается ли путь с целевого (prefix matching)
        if hit_path_normalized and target_path_normalized:
            # Точное совпадение пути
            if hit_path_normalized == target_path_normalized:
                return True
            # Prefix matching: hit начинается с target
            if hit_path_normalized.startswith(target_path_normalized + '/') or hit_path_normalized.startswith(target_path_normalized):
                return True
            # Обратный вариант: /bachelor/ <-> /base/
            hit_path_alt = hit_path.replace('/bachelor/', '/base/')
            target_path_alt = target_path.replace('/bachelor/', '/base/')
            if hit_path_alt == target_path_alt or hit_path_alt.startswith(target_path_alt + '/') or hit_path_alt.startswith(target_path_alt):
                return True
        
        return False
    
    return False


def check_step_achieved(session: VisitSession, step: Dict[str, Any], goal_parser: GoalParser, hits: List[PageHit]) -> bool:
    """
    Проверяет, достигнут ли шаг воронки в данной сессии
    
    Args:
        session: VisitSession объект
        step: Конфигурация шага
        goal_parser: Парсер целей
        hits: Список hits сессии
    
    Returns:
        bool: True если шаг достигнут
    """
    step_type = step.get('type')
    
    if step_type == 'goal':
        goal_code = step.get('code')
        goal_config = goal_parser.get_goal_by_code(goal_code)
        
        if not goal_config:
            return False
        
        match_type = goal_config['match']['type']
        
        if match_type == 'identifier':
            # Проверяем через goalsID в сессии
            goal_id = goal_config.get('ym_goal_id')
            if goal_id:
                session_goals = session.goals_id or []
                return goal_id in session_goals
            return False
        else:
            # URL-based или другие типы - проверяем через hits
            for hit in hits:
                if matches_funnel_step(hit, step, goal_parser):
                    return True
            return False
    
    elif step_type == 'url':
        # URL шаг - проверяем через hits
        for hit in hits:
            if matches_funnel_step(hit, step, goal_parser):
                return True
        return False
    
    return False


def calculate_funnel_metrics(
    funnel: ConversionFunnel,
    version,
    client_ids_filter: Optional[Set[str]] = None,
    goal_parser: Optional[GoalParser] = None
) -> Dict[str, Any]:
    """
    Рассчитывает метрики воронки для заданной версии
    
    Args:
        funnel: Объект ConversionFunnel
        version: ProductVersion объект
        client_ids_filter: Опциональный фильтр по client_ids (для анализа по когортам)
        goal_parser: Парсер целей (если не передан, создается новый)
    
    Returns:
        Dict с метриками воронки
    """
    if goal_parser is None:
        goal_parser = GoalParser()
    
    steps = funnel.steps
    if not steps:
        return {
            'total_entered': 0,
            'total_completed': 0,
            'overall_conversion': 0.0,
            'step_metrics': []
        }
    
    # Получаем все сессии версии
    sessions_query = VisitSession.objects.filter(version=version)
    if client_ids_filter:
        sessions_query = sessions_query.filter(client_id__in=client_ids_filter)
    
    sessions = sessions_query.prefetch_related('hits')
    
    # Собираем client_ids, которые достигли каждого шага
    step_client_ids = {}
    for step_idx in range(len(steps)):
        step_client_ids[step_idx] = set()
    
    # Проходим по всем сессиям и проверяем шаги
    for session in sessions:
        # Получаем hits сессии в хронологическом порядке
        hits = list(session.hits.all().order_by('timestamp'))
        client_id = session.client_id
        
        # Для последовательных воронок проверяем шаги по порядку
        if funnel.require_sequence:
            current_step_idx = 0
            for step_idx in range(len(steps)):
                if step_idx != current_step_idx:
                    continue  # Пропускаем шаги, которые не являются текущими
                
                step = steps[step_idx]
                if check_step_achieved(session, step, goal_parser, hits):
                    step_client_ids[step_idx].add(client_id)
                    current_step_idx = step_idx + 1
                    if current_step_idx >= len(steps):
                        break  # Воронка завершена
                else:
                    # Если шаг не достигнут, останавливаемся (для последовательных воронок)
                    break
        else:
            # Для непоследовательных воронок проверяем все шаги независимо
            for step_idx, step in enumerate(steps):
                if check_step_achieved(session, step, goal_parser, hits):
                    step_client_ids[step_idx].add(client_id)
    
    # Рассчитываем метрики
    total_entered = len(step_client_ids.get(0, set())) if step_client_ids else 0
    total_completed = len(step_client_ids.get(len(steps) - 1, set())) if step_client_ids else 0
    
    overall_conversion = (total_completed / total_entered * 100) if total_entered > 0 else 0.0
    
    # Метрики по шагам
    step_metrics = []
    prev_count = total_entered
    
    for step_idx, step in enumerate(steps):
        users_reached = len(step_client_ids.get(step_idx, set()))
        conversion_from_prev = (users_reached / prev_count * 100) if prev_count > 0 else 0.0
        drop_off = prev_count - users_reached
        drop_off_percentage = (drop_off / prev_count * 100) if prev_count > 0 else 0.0
        
        step_metrics.append({
            'step_number': step_idx + 1,
            'step_name': step.get('name', f'Шаг {step_idx + 1}'),
            'step_type': step.get('type'),
            'step_code': step.get('code') or step.get('url'),
            'users_reached': users_reached,
            'conversion_from_prev': round(conversion_from_prev, 2),
            'drop_off': drop_off,
            'drop_off_percentage': round(drop_off_percentage, 2)
        })
        
        prev_count = users_reached
    
    return {
        'total_entered': total_entered,
        'total_completed': total_completed,
        'overall_conversion': round(overall_conversion, 2),
        'step_metrics': step_metrics
    }


def calculate_funnel_metrics_by_cohorts(
    funnel: ConversionFunnel,
    version,
    goal_parser: Optional[GoalParser] = None
) -> Dict[str, Any]:
    """
    Рассчитывает метрики воронки с разбивкой по когортам
    
    Returns:
        Dict с метриками по каждой когорте
    """
    if goal_parser is None:
        goal_parser = GoalParser()
    
    cohorts = UserCohort.objects.filter(version=version)
    cohort_breakdown = {}
    
    for cohort in cohorts:
        # Получаем client_ids этой когорты
        cohort_client_ids = set(cohort.member_client_ids or [])
        
        if not cohort_client_ids:
            continue
        
        # Рассчитываем метрики воронки для этой когорты
        metrics = calculate_funnel_metrics(
            funnel=funnel,
            version=version,
            client_ids_filter=cohort_client_ids,
            goal_parser=goal_parser
        )
        
        cohort_breakdown[cohort.id] = {
            'cohort_id': cohort.id,
            'cohort_name': cohort.name,
            'users_in_cohort': cohort.users_count,
            'funnel_metrics': metrics,
            'users_entered_funnel': metrics['total_entered'],
            'users_completed_funnel': metrics['total_completed'],
            'conversion_rate': metrics['overall_conversion'],
            'funnel_participation_rate': round(
                (metrics['total_entered'] / cohort.users_count * 100) if cohort.users_count > 0 else 0,
                2
            )
        }
    
    return cohort_breakdown
