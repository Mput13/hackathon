"""
Автоматическое обнаружение воронок на основе реальных путей пользователей
Использует анализ частых последовательностей URL для создания воронок
"""
from typing import List, Dict, Set, Tuple, Any, Optional
from collections import defaultdict, Counter
from django.db.models import Q
from analytics.models import VisitSession, PageHit, ProductVersion, UserCohort
from analytics.utils import GoalParser


def normalize_url_for_discovery(url: str) -> str:
    """
    Нормализация URL для обнаружения воронок
    Убирает параметры, оставляет только путь для группировки похожих URL
    Приводит /base/ и /bachelor/ к одному виду для группировки
    Убирает расширения файлов (.php, .html) для лучшей группировки
    """
    if not isinstance(url, str):
        return ""
    
    from urllib.parse import urlparse
    
    # Парсим URL
    parsed = urlparse(url.strip())
    path = (parsed.path or "/").rstrip("/") or "/"
    
    # Нормализуем: /base/ и /bachelor/ считаются эквивалентными
    path = path.replace('/base/', '/bachelor/')
    
    # Убираем расширения файлов для лучшей группировки
    import re
    path = re.sub(r'\.(php|html|htm|aspx|jsp)$', '', path, flags=re.IGNORECASE)
    
    # Убираем специфичные части пути (ID, хэши, даты)
    # Например: /bachelor/programs/item/12345 -> /bachelor/programs/item/
    # /prikazy-o-zachislenii-2022.php -> /prikazy-o-zachislenii/
    parts = [p for p in path.split('/') if p]
    
    # Фильтруем части, которые выглядят как ID или даты
    filtered_parts = []
    for part in parts:
        # Пропускаем части, которые выглядят как чисто числовые ID или короткие коды
        if part.isdigit() and len(part) > 3:
            continue
        # Пропускаем части с датами (например, "2022")
        if part.isdigit() and (part.startswith('20') or part.startswith('19')):
            continue
        # Пропускаем очень короткие коды (вероятно, специфичные ID)
        if len(part) <= 2 and part.isalnum():
            continue
        filtered_parts.append(part)
    
    parts = filtered_parts
    
    # Ограничиваем глубину пути для группировки похожих страниц
    # Оставляем максимум 4 уровня для сохранения больше деталей (было 3)
    if len(parts) > 4:
        # Оставляем первые 4 уровня: /level1/level2/level3/level4/
        path = '/' + '/'.join(parts[:4]) + '/'
    else:
        path = '/' + '/'.join(parts) + '/' if parts else '/'
    
    return path


def extract_user_paths(version: ProductVersion, min_steps: int = 2, max_steps: int = 5) -> List[List[str]]:
    """
    Извлекает пути пользователей (последовательности URL) из данных
    Оптимизировано для работы с большими объемами данных
    
    Args:
        version: Версия продукта
        min_steps: Минимальное количество шагов в пути
        max_steps: Максимальное количество шагов в пути
    
    Returns:
        Список путей, каждый путь - список нормализованных URL
    """
    paths = []
    
    # Используем iterator() для потоковой обработки больших объемов данных
    # prefetch_related('hits') загружает все hits сразу для каждой сессии
    sessions = VisitSession.objects.filter(version=version).prefetch_related('hits').iterator(chunk_size=1000)
    
    session_count = 0
    for session in sessions:
        session_count += 1
        
        # Получаем hits в хронологическом порядке (уже загружены через prefetch_related)
        hits = list(session.hits.all())
        hits.sort(key=lambda h: h.timestamp)
        
        # Нормализуем URL и убираем дубликаты подряд
        normalized_urls = []
        prev_url = None
        for hit in hits:
            normalized = normalize_url_for_discovery(hit.url)
            if normalized and normalized != prev_url:  # Убираем дубликаты подряд
                normalized_urls.append(normalized)
                prev_url = normalized
        
        # Фильтруем по длине
        if min_steps <= len(normalized_urls) <= max_steps:
            # Убираем слишком общие страницы (например, только главная)
            if len(set(normalized_urls)) > 1:  # Должно быть хотя бы 2 разных страницы
                paths.append(normalized_urls)
    
    return paths


def find_frequent_sequences(paths: List[List[str]], min_support: int = 5) -> List[Tuple[List[str], int]]:
    """
    Находит частые последовательности URL в путях пользователей
    
    Args:
        paths: Список путей пользователей
        min_support: Минимальное количество вхождений для включения в результат
    
    Returns:
        Список кортежей (последовательность, количество вхождений), отсортированный по частоте
    """
    # Считаем все последовательности длиной от 2 до 4 шагов
    sequence_counts = Counter()
    
    for path in paths:
        # Генерируем все подпоследовательности длины 2-4
        for length in range(2, min(5, len(path) + 1)):
            for i in range(len(path) - length + 1):
                sequence = tuple(path[i:i+length])
                sequence_counts[sequence] += 1
    
    # Фильтруем по минимальной поддержке
    frequent = [
        (list(seq), count)
        for seq, count in sequence_counts.items()
        if count >= min_support
    ]
    
    # Сортируем по частоте (по убыванию)
    frequent.sort(key=lambda x: x[1], reverse=True)
    
    return frequent


def filter_redundant_sequences(sequences: List[Tuple[List[str], int]]) -> List[Tuple[List[str], int]]:
    """
    Фильтрует избыточные последовательности
    Убирает подпоследовательности, если есть более длинная последовательность с такой же частотой
    """
    if not sequences:
        return []
    
    # Сортируем по длине (от больших к меньшим) и частоте
    sequences_sorted = sorted(sequences, key=lambda x: (-len(x[0]), -x[1]))
    
    filtered = []
    seen_prefixes = set()
    
    for seq, count in sequences_sorted:
        seq_tuple = tuple(seq)
        
        # Проверяем, не является ли это подпоследовательностью уже добавленной
        is_subsequence = False
        for existing_seq_tuple in seen_prefixes:
            if len(seq) < len(existing_seq_tuple):
                # Проверяем, содержится ли seq в existing_seq
                seq_str = '|'.join(seq)
                existing_str = '|'.join(existing_seq_tuple)
                if seq_str in existing_str:
                    is_subsequence = True
                    break
        
        if not is_subsequence:
            filtered.append((seq, count))
            seen_prefixes.add(seq_tuple)
    
    return filtered


def sequences_to_funnels(
    sequences: List[Tuple[List[str], int]],
    version: ProductVersion,
    min_frequency: int = 5
) -> List[Dict[str, Any]]:
    """
    Преобразует найденные последовательности в конфигурацию воронок
    
    Args:
        sequences: Список кортежей (последовательность, частота)
        version: Версия продукта
        min_frequency: Минимальная частота для создания воронки
    
    Returns:
        Список конфигураций воронок
    """
    funnels = []
    
    for seq, frequency in sequences:
        if frequency < min_frequency:
            continue
        
        # Создаем полные URL из путей
        base_url = 'https://priem.mai.ru'
        steps = []
        
        for i, path in enumerate(seq):
            # Формируем полный URL
            # Если путь нормализован как /bachelor/, используем /base/ для 2024
            url_path = path.replace('/bachelor/', '/base/')
            full_url = base_url + (url_path if url_path.startswith('/') else '/' + url_path)
            
            # Генерируем имя шага из пути
            path_parts = [p for p in url_path.strip('/').split('/') if p]
            if path_parts:
                # Используем последнюю часть пути для имени, убираем расширения
                last_part = path_parts[-1]
                # Убираем расширения файлов
                import re
                last_part = re.sub(r'\.(php|html|htm|aspx|jsp)$', '', last_part, flags=re.IGNORECASE)
                # Заменяем дефисы и подчеркивания на пробелы
                step_name = last_part.replace('-', ' ').replace('_', ' ').title()
                # Если имя слишком длинное, используем предпоследнюю часть
                if len(step_name) > 40 and len(path_parts) > 1:
                    step_name = path_parts[-2].replace('-', ' ').replace('_', ' ').title()
            else:
                step_name = 'Главная страница'
            
            steps.append({
                'type': 'url',
                'url': full_url,
                'name': step_name
            })
        
        if len(steps) >= 2:
            # Генерируем имя воронки из путей
            path_names = [step['name'] for step in steps]
            if len(path_names) == 2:
                funnel_name = f"{path_names[0]} → {path_names[1]} (auto, {frequency})"
            else:
                funnel_name = f"{path_names[0]} → ... → {path_names[-1]} (auto, {frequency})"
            
            # Описание с деталями
            path_str = " → ".join(seq)
            funnels.append({
                'name': funnel_name,
                'description': f'Автоматически обнаруженная воронка на основе реальных данных. {frequency} пользователей прошли этот путь: {path_str}',
                'steps': steps,
                'is_preset': False,  # Автоматически созданные
                'frequency': frequency
            })
    
    return funnels


def discover_funnels(
    version: ProductVersion,
    min_support: int = 15,
    min_path_length: int = 2,
    max_path_length: int = 4,
    max_funnels: int = 20,
    min_percentage: float = 0.5
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Автоматически обнаруживает воронки на основе реальных путей пользователей
    
    Args:
        version: Версия продукта
        min_support: Минимальное количество пользователей для создания воронки
        min_path_length: Минимальная длина пути
        max_path_length: Максимальная длина пути
        max_funnels: Максимальное количество воронок для создания
        min_percentage: Минимальный процент от общего числа пользователей (по умолчанию 2%)
    
    Returns:
        Кортеж: (список конфигураций воронок, статистика)
    """
    # Получаем общее количество сессий для расчета процентов
    total_sessions = VisitSession.objects.filter(version=version).count()
    
    # Если min_support не задан явно, рассчитываем от процента
    if min_support < 10:  # Если слишком маленький, используем процент
        min_support_from_percent = int(total_sessions * min_percentage / 100)
        min_support = max(min_support, min_support_from_percent)
    
    stats = {
        'total_sessions': total_sessions,
        'min_support_used': min_support,
        'min_percentage': min_percentage
    }
    
    # 1. Извлекаем пути пользователей
    paths = extract_user_paths(version, min_steps=min_path_length, max_steps=max_path_length)
    stats['total_paths_extracted'] = len(paths)
    
    if not paths:
        return [], stats
    
    # 2. Находим частые последовательности
    frequent_sequences = find_frequent_sequences(paths, min_support=min_support)
    stats['frequent_sequences_found'] = len(frequent_sequences)
    
    if not frequent_sequences:
        return [], stats
    
    # 3. Фильтруем избыточные последовательности
    filtered_sequences = filter_redundant_sequences(frequent_sequences)
    stats['filtered_sequences'] = len(filtered_sequences)
    
    # 4. Дополнительная фильтрация по проценту
    final_sequences = []
    for seq, count in filtered_sequences:
        percentage = (count / total_sessions) * 100 if total_sessions > 0 else 0
        if percentage >= min_percentage:
            final_sequences.append((seq, count, percentage))
    
    # Сортируем по проценту (убывание)
    final_sequences.sort(key=lambda x: x[2], reverse=True)
    
    stats['final_sequences_after_percentage_filter'] = len(final_sequences)
    
    # 5. Преобразуем в воронки
    funnels = sequences_to_funnels(
        [(seq, count) for seq, count, _ in final_sequences[:max_funnels]],
        version,
        min_frequency=min_support
    )
    
    # Добавляем процент в описание
    for funnel, (_, _, percentage) in zip(funnels, final_sequences[:len(funnels)]):
        funnel['percentage'] = round(percentage, 2)
        funnel['description'] += f' ({percentage:.1f}% от общего числа пользователей)'
    
    return funnels, stats


def extract_user_paths_with_goals(
    version: ProductVersion,
    client_ids_filter: Optional[Set[str]] = None,
    min_steps: int = 2,
    max_steps: int = 5,
    goal_parser: Optional[GoalParser] = None,
    debug_stats: Optional[Dict[str, Any]] = None
) -> Tuple[List[List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Извлекает пути пользователей с учетом URL и целей (goals)
    Каждый шаг пути - это словарь с типом ('url' или 'goal') и данными
    
    Args:
        version: Версия продукта
        client_ids_filter: Опциональный фильтр по client_ids (для когорт)
        min_steps: Минимальное количество шагов в пути
        max_steps: Максимальное количество шагов в пути
        goal_parser: Парсер целей (если не передан, создается новый)
    
    Returns:
        Список путей, каждый путь - список словарей {'type': 'url'|'goal', ...}
    """
    if goal_parser is None:
        goal_parser = GoalParser()
    
    paths = []
    
    # Фильтруем сессии
    sessions_query = VisitSession.objects.filter(version=version)
    if client_ids_filter:
        # Преобразуем в строки для сравнения
        client_ids_filter_str = {str(cid) for cid in client_ids_filter}
        sessions_query = sessions_query.filter(client_id__in=client_ids_filter_str)
    
    total_sessions = sessions_query.count()
    sessions = sessions_query.prefetch_related('hits').iterator(chunk_size=1000)
    
    # Отладочная статистика
    sessions_with_hits = 0
    sessions_without_hits = 0
    paths_filtered_by_length = 0
    paths_filtered_by_uniqueness = 0
    
    # Создаем маппинг goal_id -> goal_code для быстрого поиска
    goal_id_to_code = {}
    for goal in goal_parser.get_goals():
        goal_id = goal.get('ym_goal_id')
        if goal_id:
            goal_id_to_code[str(goal_id)] = goal.get('code')
    
    for session in sessions:
        # Получаем hits в хронологическом порядке
        hits = list(session.hits.all())
        
        if not hits:
            sessions_without_hits += 1
            continue
        
        sessions_with_hits += 1
        hits.sort(key=lambda h: h.timestamp)
        
        # Собираем последовательность шагов (URL + Goals)
        path_steps = []
        prev_url = None
        
        # Обрабатываем hits
        for hit in hits:
            if not hit.url:
                continue
            # Добавляем URL (если не дубликат)
            normalized_url = normalize_url_for_discovery(hit.url)
            if normalized_url and normalized_url != prev_url:
                path_steps.append({
                    'type': 'url',
                    'url': hit.url,
                    'normalized_url': normalized_url,
                    'timestamp': hit.timestamp
                })
                prev_url = normalized_url
        
        # Добавляем цели из сессии (если есть)
        session_goals = session.goals_id or []
        for goal_id in session_goals:
            goal_code = goal_id_to_code.get(str(goal_id))
            if goal_code:
                goal_config = goal_parser.get_goal_by_code(goal_code)
                if goal_config:
                    # Вставляем цель в последовательность (по timestamp сессии)
                    path_steps.append({
                        'type': 'goal',
                        'code': goal_code,
                        'name': goal_config.get('name', goal_code),
                        'goal_id': goal_id,
                        'timestamp': session.start_time  # Используем время начала сессии
                    })
        
        # Сортируем по timestamp
        path_steps.sort(key=lambda x: x['timestamp'])
        
        # Нормализуем: убираем дубликаты подряд, оставляем только уникальные шаги
        normalized_steps = []
        prev_step = None
        for step in path_steps:
            # Для URL сравниваем normalized_url
            if step['type'] == 'url':
                if prev_step is None or prev_step.get('normalized_url') != step['normalized_url']:
                    normalized_steps.append(step)
                    prev_step = step
            # Для целей всегда добавляем (они уникальны по goal_id)
            elif step['type'] == 'goal':
                # Проверяем, не добавляли ли мы уже эту цель
                if not any(s.get('goal_id') == step['goal_id'] for s in normalized_steps):
                    normalized_steps.append(step)
                    prev_step = step
        
        # Фильтруем по длине
        if len(normalized_steps) < min_steps:
            continue
        if len(normalized_steps) > max_steps:
            paths_filtered_by_length += 1
            continue
        
        # Убираем слишком общие пути (только одна страница)
        unique_steps = len(set(
            s.get('normalized_url', '') if s['type'] == 'url' else f"goal:{s.get('code')}"
            for s in normalized_steps
        ))
        
        # Для путей с min_steps=1 разрешаем только если есть цели
        if min_steps == 1:
            has_goal = any(s['type'] == 'goal' for s in normalized_steps)
            if has_goal and unique_steps >= 1:
                paths.append(normalized_steps)
            else:
                paths_filtered_by_uniqueness += 1
        elif unique_steps > 1:  # Для остальных должно быть хотя бы 2 разных шага
            paths.append(normalized_steps)
        else:
            paths_filtered_by_uniqueness += 1
    
    # Формируем отладочную статистику
    debug_info = {
        'total_sessions': total_sessions,
        'sessions_with_hits': sessions_with_hits,
        'sessions_without_hits': sessions_without_hits,
        'paths_filtered_by_length': paths_filtered_by_length,
        'paths_filtered_by_uniqueness': paths_filtered_by_uniqueness,
        'final_paths_count': len(paths)
    }
    
    if debug_stats is not None:
        debug_stats.update(debug_info)
    
    return paths, debug_info


def find_frequent_sequences_with_goals(
    paths: List[List[Dict[str, Any]]],
    min_support: int = 5
) -> List[Tuple[List[Dict[str, Any]], int]]:
    """
    Находит частые последовательности в путях пользователей (с учетом URL и целей)
    
    Args:
        paths: Список путей пользователей (каждый путь - список словарей шагов)
        min_support: Минимальное количество вхождений для включения в результат
    
    Returns:
        Список кортежей (последовательность, количество вхождений), отсортированный по частоте
    """
    # Используем словарь для хранения последовательностей и их счетчиков
    sequence_data = {}  # key: tuple -> (sequence, count)
    
    for path in paths:
        # Генерируем все подпоследовательности длины 2-4
        for length in range(2, min(5, len(path) + 1)):
            for i in range(len(path) - length + 1):
                sequence = path[i:i+length]
                # Создаем ключ для последовательности (нормализованный)
                sequence_key = []
                for step in sequence:
                    if step['type'] == 'url':
                        key = f"url:{step.get('normalized_url', '')}"
                    else:  # goal
                        key = f"goal:{step.get('code', '')}"
                    sequence_key.append(key)
                
                seq_key_tuple = tuple(sequence_key)
                
                # Сохраняем последовательность и увеличиваем счетчик
                if seq_key_tuple not in sequence_data:
                    sequence_data[seq_key_tuple] = {
                        'sequence': sequence,
                        'count': 0
                    }
                sequence_data[seq_key_tuple]['count'] += 1
    
    # Фильтруем по минимальной поддержке и формируем результат
    frequent = []
    for seq_key_tuple, data in sequence_data.items():
        count = data['count']
        if count >= min_support:
            frequent.append((data['sequence'], count))
    
    # Сортируем по частоте (по убыванию)
    frequent.sort(key=lambda x: x[1], reverse=True)
    
    return frequent


def sequences_to_funnels_with_goals(
    sequences: List[Tuple[List[Dict[str, Any]], int]],
    version: ProductVersion,
    cohort_name: Optional[str] = None,
    min_frequency: int = 5
) -> List[Dict[str, Any]]:
    """
    Преобразует найденные последовательности (с целями) в конфигурацию воронок
    
    Args:
        sequences: Список кортежей (последовательность шагов, частота)
        version: Версия продукта
        cohort_name: Название когорты (для именования воронок)
        min_frequency: Минимальная частота для создания воронки
    
    Returns:
        Список конфигураций воронок
    """
    funnels = []
    base_url = 'https://priem.mai.ru'
    
    for seq, frequency in sequences:
        if frequency < min_frequency:
            continue
        
        steps = []
        step_names = []
        
        for step in seq:
            if step['type'] == 'url':
                # URL шаг
                url = step.get('url', '')
                normalized_url = step.get('normalized_url', '')
                
                # Формируем полный URL
                url_path = normalized_url.replace('/bachelor/', '/base/')
                if not url_path.startswith('http'):
                    full_url = base_url + (url_path if url_path.startswith('/') else '/' + url_path)
                else:
                    full_url = url
                
                # Генерируем имя шага из оригинального URL, а не нормализованного
                # Используем оригинальный URL для более точного имени
                original_url = url if url else full_url
                from urllib.parse import urlparse
                parsed_original = urlparse(original_url)
                original_path = parsed_original.path or "/"
                
                # Генерируем имя шага
                path_parts = [p for p in original_path.strip('/').split('/') if p]
                if path_parts:
                    # Берем последнюю значимую часть пути
                    last_part = path_parts[-1]
                    import re
                    last_part = re.sub(r'\.(php|html|htm|aspx|jsp)$', '', last_part, flags=re.IGNORECASE)
                    step_name = last_part.replace('-', ' ').replace('_', ' ').title()
                    
                    # Если имя слишком общее или длинное, используем предпоследнюю часть
                    if (len(step_name) > 40 or step_name.lower() in ['programs', 'program', 'index', 'main']) and len(path_parts) > 1:
                        step_name = path_parts[-2].replace('-', ' ').replace('_', ' ').title()
                    
                    # Если все еще слишком общее, используем комбинацию
                    if step_name.lower() in ['programs', 'program'] and len(path_parts) > 2:
                        step_name = f"{path_parts[-3].replace('-', ' ').replace('_', ' ').title()} → {step_name}"
                else:
                    step_name = 'Главная страница'
                
                steps.append({
                    'type': 'url',
                    'url': full_url,
                    'name': step_name
                })
                step_names.append(step_name)
            
            elif step['type'] == 'goal':
                # Goal шаг
                goal_code = step.get('code', '')
                goal_name = step.get('name', goal_code)
                
                steps.append({
                    'type': 'goal',
                    'code': goal_code,
                    'name': goal_name
                })
                step_names.append(goal_name)
        
        if len(steps) >= 2:
            # Генерируем имя воронки
            if cohort_name:
                if len(step_names) == 2:
                    funnel_name = f"{cohort_name}: {step_names[0]} → {step_names[1]}"
                else:
                    funnel_name = f"{cohort_name}: {step_names[0]} → ... → {step_names[-1]}"
            else:
                if len(step_names) == 2:
                    funnel_name = f"{step_names[0]} → {step_names[1]} (auto, {frequency})"
                else:
                    funnel_name = f"{step_names[0]} → ... → {step_names[-1]} (auto, {frequency})"
            
            # Описание
            path_str = " → ".join(step_names)
            if cohort_name:
                description = f'Автоматически обнаруженная воронка для когорты "{cohort_name}". {frequency} пользователей прошли этот путь: {path_str}'
            else:
                description = f'Автоматически обнаруженная воронка. {frequency} пользователей прошли этот путь: {path_str}'
            
            funnels.append({
                'name': funnel_name,
                'description': description,
                'steps': steps,
                'is_preset': False,
                'frequency': frequency
            })
    
    return funnels


def discover_funnels_for_cohort(
    cohort: UserCohort,
    version: ProductVersion,
    min_support: int = 3,
    min_path_length: int = 2,
    max_path_length: int = 5,
    max_funnels: int = 5,
    goal_parser: Optional[GoalParser] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Автоматически обнаруживает воронки для конкретной когорты
    
    Args:
        cohort: Когорта пользователей
        version: Версия продукта
        min_support: Минимальное количество пользователей для создания воронки
        min_path_length: Минимальная длина пути
        max_path_length: Максимальная длина пути
        max_funnels: Максимальное количество воронок для создания
        goal_parser: Парсер целей (если не передан, создается новый)
    
    Returns:
        Кортеж: (список конфигураций воронок, статистика)
    """
    if goal_parser is None:
        goal_parser = GoalParser()
    
    # Получаем client_ids когорты
    cohort_client_ids = set(cohort.member_client_ids or [])
    
    if not cohort_client_ids:
        return [], {
            'cohort_name': cohort.name,
            'cohort_users': cohort.users_count,
            'error': 'No client IDs in cohort'
        }
    
    stats = {
        'cohort_name': cohort.name,
        'cohort_users': cohort.users_count,
        'cohort_client_ids_count': len(cohort_client_ids),
        'min_support_used': min_support
    }
    
    # Адаптируем min_support для размера когорты
    # Для маленьких когорт: минимум 3 или 20% (что больше)
    # Для больших когорт: минимум 3 или 2% (но не больше 50)
    if cohort.users_count < 50:
        min_support_adaptive = max(min_support, max(3, int(cohort.users_count * 0.2)))
    else:
        min_support_adaptive = max(min_support, min(max(3, int(cohort.users_count * 0.02)), 50))
    stats['min_support_adaptive'] = min_support_adaptive
    
    # 1. Извлекаем пути пользователей когорты (с целями)
    # Для больших когорт увеличиваем max_steps, чтобы захватить больше путей
    adaptive_max_steps = max_path_length
    adaptive_min_steps = min_path_length
    if cohort.users_count > 100:
        adaptive_max_steps = min(max_path_length + 3, 10)  # До 10 шагов для больших когорт
        adaptive_min_steps = 1  # Разрешаем пути от 1 шага для больших когорт
    
    paths, debug_info = extract_user_paths_with_goals(
        version=version,
        client_ids_filter=cohort_client_ids,
        min_steps=adaptive_min_steps,
        max_steps=adaptive_max_steps,
        goal_parser=goal_parser,
        debug_stats=stats
    )
    
    # Обновляем статистику отладочной информацией
    stats.update(debug_info)
    
    stats['total_paths_extracted'] = len(paths)
    stats['adaptive_max_steps'] = adaptive_max_steps
    stats['adaptive_min_steps'] = adaptive_min_steps
    
    # Дополнительная статистика для отладки
    if paths:
        path_lengths = [len(p) for p in paths]
        stats['avg_path_length'] = sum(path_lengths) / len(path_lengths) if path_lengths else 0
        stats['min_path_length'] = min(path_lengths) if path_lengths else 0
        stats['max_path_length'] = max(path_lengths) if path_lengths else 0
    
    if not paths:
        return [], stats
    
    # 2. Находим частые последовательности
    frequent_sequences = find_frequent_sequences_with_goals(paths, min_support=min_support_adaptive)
    stats['frequent_sequences_found'] = len(frequent_sequences)
    
    if not frequent_sequences:
        return [], stats
    
    # 3. Фильтруем избыточные последовательности
    # Убираем подпоследовательности, если есть более длинная с такой же или большей частотой
    filtered_sequences = []
    seen_sequences = set()
    
    # Сортируем по длине (от больших к меньшим) и частоте
    sorted_sequences = sorted(frequent_sequences, key=lambda x: (-len(x[0]), -x[1]))
    
    for seq, count in sorted_sequences:
        # Создаем ключ для последовательности
        seq_key = tuple(
            f"url:{s.get('normalized_url', '')}" if s['type'] == 'url' else f"goal:{s.get('code', '')}"
            for s in seq
        )
        
        # Проверяем, не является ли это подпоследовательностью уже добавленной
        is_subsequence = False
        for existing_key in seen_sequences:
            existing_parts = list(existing_key)
            seq_parts = list(seq_key)
            
            # Проверяем, содержится ли seq_parts в existing_parts как подпоследовательность
            if len(seq_parts) < len(existing_parts):
                # Ищем seq_parts в existing_parts
                i = 0
                for part in existing_parts:
                    if i < len(seq_parts) and seq_parts[i] == part:
                        i += 1
                if i == len(seq_parts):
                    is_subsequence = True
                    break
        
        if not is_subsequence:
            filtered_sequences.append((seq, count))
            seen_sequences.add(seq_key)
    
    stats['filtered_sequences'] = len(filtered_sequences)
    
    # 4. Валидация последовательностей перед созданием воронок
    validated_sequences = []
    for seq, count in filtered_sequences[:max_funnels * 2]:
        # Валидация: должна быть хотя бы одна URL или одна цель
        has_url = any(s['type'] == 'url' for s in seq)
        has_goal = any(s['type'] == 'goal' for s in seq)
        
        if not (has_url or has_goal):
            continue
        
        # Валидация: не должно быть только целей без URL (нужен хотя бы один URL для контекста)
        if not has_url:
            continue
        
        # Валидация: минимум 2 уникальных шага
        unique_steps = len(set(
            s.get('normalized_url', '') if s['type'] == 'url' else f"goal:{s.get('code')}"
            for s in seq
        ))
        if unique_steps < 2:
            continue
        
        validated_sequences.append((seq, count))
    
    stats['validated_sequences'] = len(validated_sequences)
    
    # 5. Преобразуем в воронки
    funnels = sequences_to_funnels_with_goals(
        validated_sequences[:max_funnels],
        version=version,
        cohort_name=cohort.name,
        min_frequency=min_support_adaptive
    )
    
    # Дополнительная валидация созданных воронок
    final_funnels = []
    for funnel in funnels:
        # Проверяем, что воронка имеет минимум 2 шага
        if len(funnel['steps']) < 2:
            continue
        
        # Проверяем, что есть хотя бы один URL шаг
        has_url_step = any(s['type'] == 'url' for s in funnel['steps'])
        if not has_url_step:
            continue
        
        final_funnels.append(funnel)
    
    stats['funnels_created'] = len(final_funnels)
    
    return final_funnels, stats

