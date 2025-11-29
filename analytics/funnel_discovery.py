"""
Автоматическое обнаружение воронок на основе реальных путей пользователей
Использует анализ частых последовательностей URL для создания воронок
"""
from typing import List, Dict, Set, Tuple, Any
from collections import defaultdict, Counter
from django.db.models import Q
from analytics.models import VisitSession, PageHit, ProductVersion
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
    # Оставляем максимум 2-3 уровня для избежания слишком специфичных путей
    if len(parts) > 3:
        # Оставляем первые 3 уровня: /level1/level2/level3/
        path = '/' + '/'.join(parts[:3]) + '/'
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

