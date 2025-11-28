import os
import sys
import json
try:
    import requests
except ImportError:
    requests = None

# Human-readable examples (подсказки, не жесткие определения)
ISSUE_EXAMPLES = {
    "HIGH_BOUNCE": "Пример: высокий отскок на ключевых страницах (ушли сразу без действия).",
    "LOOPING": "Пример: блуждание/возвраты (много переходов без прогресса).",
    "DEAD_CLICK": "Пример: мёртвые клики (элемент без реакции или ошибка).",
    "RAGE_CLICK": "Пример: rage/повторные клики по одному месту за короткое время.",
    "FORM_ABANDON": "Пример: проблемы с формами (долгий ввод, правки, брошенные формы).",
    "FUNNEL_DROPOFF": "Пример: критические точки отказа в воронке (аномальный отток на шаге).",
}

# Получаем креды из ENV
FOLDER_ID = os.environ.get("FOLDER_ID") or os.environ.get("folder_id")
API_KEY = os.environ.get("API_KEY") or os.environ.get("api_key")

def _send_gpt_request(system_text, user_text):
    """Helper to send request to YandexGPT"""
    if not FOLDER_ID or not API_KEY or requests is None:
        return None

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {API_KEY}",
        "x-folder-id": FOLDER_ID
    }

    body = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.3,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "system",
                "text": system_text
            },
            {
                "role": "user",
                "text": user_text
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        
        if response.status_code != 200:
            print(f"YandexAI Error: Status {response.status_code}, Body: {response.text}")
            return None
            
        result = response.json()
        return result['result']['alternatives'][0]['message']['text']

    except Exception as e:
        print(f"YandexAI Exception: {e}")
        return None

def analyze_issue_with_ai(issue_type, location, metrics_context, 
                         page_title=None, page_metrics=None, 
                         dominant_cohort=None, dominant_device=None):
    """
    Отправляет запрос в Yandex Foundation Models (YandexGPT) через REST API.
    Использует расширенный контекст с метриками страницы для более точных гипотез.
    """
    # Формируем расширенный контекст
    context_parts = [f"URL: {location}"]
    issue_hint = ISSUE_EXAMPLES.get(issue_type)
    if issue_hint:
        context_parts.append(f"Пример проявления: {issue_hint}")
    
    if page_title:
        context_parts.append(f"Заголовок страницы: {page_title}")
    
    if page_metrics:
        if page_metrics.get('avg_time'):
            context_parts.append(f"Среднее время на странице: {page_metrics['avg_time']:.1f} сек")
        if page_metrics.get('exit_rate'):
            context_parts.append(f"Процент выходов: {page_metrics['exit_rate']:.1f}%")
        if page_metrics.get('scroll_depth'):
            context_parts.append(f"Глубина прокрутки: {page_metrics['scroll_depth']:.1f}%")
    
    if dominant_cohort:
        context_parts.append(f"Основная аудитория: {dominant_cohort}")
    
    if dominant_device:
        context_parts.append(f"Преобладающее устройство: {dominant_device}")
    
    full_context = "\n".join(context_parts)
    
    prompt_content = f"""
    Ты разбираешь инцидент UX на портале Приемной Комиссии университета.
    {full_context}
    
    Тип проблемы: {issue_type}
    Метрики: {metrics_context}
    
    Требования к ответу:
    - Без вступлений и извинений.
    - Две строки: "Гипотеза:" и "Исправить:".
    - Гипотеза: конкретная причина с привязкой к данным (не общая формулировка).
    - Исправить: конкретное изменение UI/контента/логики. Запрещены советы вида "проверить/отладить/исправить", упоминания кнопок "Назад/Вперед" и абстрактные формулировки. Пиши действие, которое сразу внедряется: добавить заметный CTA/редирект, вынести целевую ссылку из фильтра, упростить путь, укоротить форму, заменить мертвый линк.
    - Избегай дублирования причины в блоке "Исправить".
    - Длина блока "Исправить" до 140 символов.
    - Учитывай специфику приемной комиссии (абитуриенты, списки, формы).
    """
    
    system_text = """
    Ты главный UX-аналитик портала Приемной Комиссии университета.
    Твои пользователи - абитуриенты (стресс, спешка, поиск списков) и их родители.
    Интерпретируй метрики с учетом специфики:
    - Быстрый уход со списков (exit_rate >80%, time_on_page <30 сек) - это ОК (нашел себя).
    - Яростные клики на "Подать согласие" - КРИТИЧНО.
    - Многократные обновления ЛК - это ожидание результатов, не ошибка навигации.
    - Высокий scroll_depth на странице с формой - хорошо (читают внимательно).
    Отвечай четко, без воды и без QA-советов, давай конкретные продуктовые изменения (CTA, навигация, редиректы, тексты, форма).
    """
    
    result = _send_gpt_request(system_text, prompt_content)
    return result if result else generate_stub_hypothesis(issue_type)

def generate_cohort_name(metrics_dict):
    """
    Генерирует название для когорты пользователей на основе их метрик.
    metrics_dict: {'bounce': 80.5, 'duration': 12, 'depth': 1.2, 'top_goals': '...', 'top_interests': '...', 'interest_codes': [...]}
    """
    top_interests = metrics_dict.get('top_interests', 'None')
    primary_interest = (metrics_dict.get('interest_codes') or [None])[0] or "None"
    primary_goal = (metrics_dict.get('top_goals') or "None").split(",")[0].strip() or "None"
    prompt_content = f"""
    Ты маркетолог-аналитик. Придумай название для сегмента пользователей веб-сайта вуза.
    Метрики сегмента:
    - Отказы (Bounce Rate): {metrics_dict.get('bounce')}%
    - Время на сайте: {metrics_dict.get('duration')} сек
    - Глубина просмотра: {metrics_dict.get('depth')} стр
    - Достигнутые цели (конверсии): {metrics_dict.get('top_goals')}
    - Основные интересы по URL: {top_interests}
    - Главный интерес: {primary_interest}. Главная цель: {primary_goal}
    
    Задача: Дай короткое, емкое название (2-4 слова), описывающее намерение и объект интереса/цель. Используй главный интерес/цель в названии, избегай общих фраз. Примеры: "Ищут рейтинги", "Читатели новостей", "Ищут контакты", "Поступающие абитуриенты", "Заполняют формы". Без абстрактных слов.
    В ответе только название, без кавычек и лишнего текста.
    """

    system_text = "Ты опытный маркетолог. Твоя задача - сегментация аудитории. Дай понятные названия по намерению, а не общие фразы."
    
    result = _send_gpt_request(system_text, prompt_content)
    
    if not result:
        # Rule-based fallback for clarity
        bounce = metrics_dict.get('bounce', 0)
        duration = metrics_dict.get('duration', 0)
        depth = metrics_dict.get('depth', 0)
        codes = metrics_dict.get('interest_codes', []) or []
        if codes:
            code = codes[0]
            mapping = {
                'rating': "Ищут рейтинги",
                'news': "Читатели новостей",
                'contacts': "Ищут контакты",
                'admission': "Готовятся поступать",
                'forms': "Заполняют формы",
                'programs': "Изучают программы",
            }
            return mapping.get(code, "Целевая группа")
        if bounce > 70 and duration < 20:
            return "Быстро ушедшие"
        if depth > 3 and duration > 60:
            return "Глубокие исследователи"
        if duration > 90 and bounce < 40:
            return "Вовлечённые пользователи"
        return "Целевая группа"
            
    return result.strip().replace('"', '').replace("'", "")

def generate_stub_hypothesis(issue_type):
    """Резервные тексты, если AI недоступен"""
    stubs = {
        'RAGE_CLICK': "Гипотеза: Клик по элементу без отклика или долгая загрузка. Исправить: добавить явный ховер/спиннер и связать действие с корректным обработчиком.",
        'DEAD_CLICK': "Гипотеза: Клик по нерабочей ссылке/кнопке. Исправить: убрать мёртвый элемент или привязать к реальному действию/редиректу.",
        'HIGH_BOUNCE': "Гипотеза: Первый экран не совпадает с ожиданием трафика или грузится медленно. Исправить: обновить H1/hero под источник и оптимизировать LCP.",
        'LOOPING': "Гипотеза: Пользователь не находит целевое действие и ходит по одному пути. Исправить: упростить путь, добавить заметный CTA и прямой линк на целевую страницу.",
        'FORM_ABANDON': "Гипотеза: Слишком много полей или ранний запрос чувствительных данных. Исправить: сократить форму и разделить на шаги с прогрессом.",
        'WANDERING': "Гипотеза: Пользователи блуждают по сайту без четкой цели. Исправить: добавить навигационные подсказки и вынести ключевые действия на главную.",
        'NAVIGATION_BACK': "Гипотеза: Пользователи часто возвращаются назад, не находя нужную информацию. Исправить: улучшить навигацию и добавить хлебные крошки.",
        'FORM_FIELD_ERRORS': "Гипотеза: Пользователи долго заполняют форму, возможно, исправляют ошибки. Исправить: добавить валидацию в реальном времени и подсказки к полям.",
        'FUNNEL_DROPOFF': "Гипотеза: Критическая точка отвала в воронке конверсии. Исправить: упростить переход между шагами и добавить прогресс-бар."
    }
    return stubs.get(issue_type, "Рекомендуется детальный анализ поведения пользователя.")
