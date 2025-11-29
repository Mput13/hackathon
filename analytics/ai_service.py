import os
import sys
import json
try:
    import requests
except ImportError:
    requests = None
# Пытаемся подхватить .env, чтобы FOLDER_ID/API_KEY были доступны в любом окружении
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.environ.get("ENV_FILE", ".env"))
except Exception:
    pass

# Human-readable examples (подсказки, не жесткие определения)
ISSUE_EXAMPLES = {
    "HIGH_BOUNCE": "Пример: высокий отскок на ключевых страницах (ушли сразу без действия).",
    "LOOPING": "Пример: блуждание/возвраты (много переходов без прогресса).",
    "DEAD_CLICK": "Пример: мёртвые клики (элемент без реакции или ошибка).",
    "RAGE_CLICK": "Пример: rage/повторные клики по одному месту за короткое время.",
    "FORM_ABANDON": "Пример: проблемы с формами (долгий ввод, правки, брошенные формы).",
    "FUNNEL_DROPOFF": "Пример: критические точки отказа в воронке (аномальный отток на шаге).",
    "SCAN_AND_DROP": "Пример: быстро проскроллил до конца и ушёл без действия.",
    "SEARCH_FAIL": "Пример: пользователь ищет, но быстро покидает страницу поиска/результатов.",
}

# Получаем креды из ENV
FOLDER_ID = os.environ.get("FOLDER_ID") or os.environ.get("folder_id")
API_KEY = os.environ.get("API_KEY") or os.environ.get("api_key")

STUB_TEMPLATES = {
    'RAGE_CLICK': "Гипотеза: Клик по элементу без отклика или долгая загрузка. Исправить: добавить явный ховер/спиннер и связать действие с корректным обработчиком.",
    'DEAD_CLICK': "Гипотеза: Клик по нерабочей ссылке/кнопке. Исправить: убрать мёртвый элемент или привязать к реальному действию/редиректу.",
    'HIGH_BOUNCE': "Гипотеза: Первый экран не совпадает с ожиданием трафика или грузится медленно. Исправить: обновить H1/hero под источник и оптимизировать LCP.",
    'LOOPING': "Гипотеза: Пользователь не находит целевое действие и ходит по одному пути. Исправить: упростить путь, добавить заметный CTA и прямой линк на целевую страницу.",
    'FORM_ABANDON': "Гипотеза: Слишком много полей или ранний запрос чувствительных данных. Исправить: сократить форму и разделить на шаги с прогрессом.",
    'WANDERING': "Гипотеза: Пользователи блуждают по сайту без четкой цели. Исправить: добавить навигационные подсказки и вынести ключевые действия на главную.",
    'NAVIGATION_BACK': "Гипотеза: Пользователи часто возвращаются назад, не находя нужную информацию. Исправить: подсветить ключевые ссылки и явно вести к целевым страницам.",
    'FORM_FIELD_ERRORS': "Гипотеза: Пользователи долго заполняют форму, возможно, исправляют ошибки. Исправить: добавить валидацию в реальном времени и подсказки к полям.",
    'FUNNEL_DROPOFF': "Гипотеза: Критическая точка отвала в воронке конверсии. Исправить: упростить переход между шагами и добавить прогресс-бар.",
    'SCAN_AND_DROP': "Гипотеза: Страница не дает ответа, пользователь быстро скроллит и уходит. Исправить: вынести ключевое действие/ответ в верхний экран.",
    'SEARCH_FAIL': "Гипотеза: Результаты поиска нерелевантны или пустые. Исправить: добавить подсказки/популярные запросы и ссылки на целевые разделы.",
}

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

def _pack_ai_json(hypothesis: str, fix: str) -> str:
    """Формирует JSON-строку для хранения ответа AI."""
    return json.dumps(
        {
            "hypothesis": (hypothesis or "").strip(),
            "fix": (fix or "").strip(),
        },
        ensure_ascii=False,
    )

def _normalize_ai_text_to_json(text: str, issue_type: str) -> str:
    """
    Приводит ответ модели к JSON {"hypothesis": "...", "fix": "..."}.
    Если формат сломан — возвращает заглушку.
    """
    if not text:
        return generate_stub_hypothesis(issue_type)

    text = text.strip()
    # Прямая попытка распарсить JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and 'hypothesis' in parsed and 'fix' in parsed:
            return _pack_ai_json(str(parsed.get('hypothesis', '')), str(parsed.get('fix', '')))
    except Exception:
        pass

    # Попытка вытащить JSON из ответа с кодовыми блоками ``` ... ```
    if "```" in text:
        stripped = text.strip().strip("`")
        # Убираем возможный префикс вида ```json
        stripped = stripped.replace("json\n", "", 1).replace("json\r\n", "", 1)
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict) and 'hypothesis' in parsed and 'fix' in parsed:
                return _pack_ai_json(str(parsed.get('hypothesis', '')), str(parsed.get('fix', '')))
        except Exception:
            pass

    # Парсим старый формат "Гипотеза:/Исправить:"
    hyp = None
    fix = None
    for line in text.splitlines():
        line_clean = line.strip()
        low = line_clean.lower()
        if low.startswith("гипотеза:"):
            hyp = line_clean.split(":", 1)[1].strip()
        elif low.startswith("исправить:") or low.startswith("решение:"):
            fix = line_clean.split(":", 1)[1].strip()

    if hyp or fix:
        return _pack_ai_json(hyp or "—", fix or "—")

    # Если модель ответила, но формат не распознан — сохраняем как гипотезу как есть,
    # чтобы не терять содержимое, и подставляем заглушку для фикса.
    return _pack_ai_json(text[:400], "—")

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
    - Ответ строго в JSON, без Markdown/текста вокруг, одна строка.
    - Поля: "hypothesis" (конкретная причина с привязкой к данным) и "fix" (конкретное действие, до 140 символов, сразу внедряемое).
    - Пиши на русском языке, без английских слов и транслита.
    - Запрещены советы вида "проверить/отладить/исправить", упоминания кнопок "Назад/Вперед" и абстрактные формулировки. Не предлагай хлебные крошки.
    - Избегай дублирования причины в поле "fix".
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
    return _normalize_ai_text_to_json(result, issue_type)

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
    Обязательно отвечай на русском языке, без латиницы и транслита.
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
    template = STUB_TEMPLATES.get(issue_type, "Рекомендуется детальный анализ поведения пользователя.")
    # Пытаемся вычленить гипотезу/фикс даже из шаблона
    hyp = None
    fix = None
    for line in template.split("."):
        line_clean = line.strip()
        low = line_clean.lower()
        if low.startswith("гипотеза:"):
            hyp = line_clean.split(":", 1)[1].strip()
        elif low.startswith("исправить:"):
            fix = line_clean.split(":", 1)[1].strip()
    return _pack_ai_json(hyp or template, fix or "—")

def get_stub_text_variants(include_legacy: bool = False):
    """
    Возвращает список возможных заглушек (JSON + опционально старые строки),
    чтобы идентифицировать их в базе при регенерации.
    """
    variants = []
    for issue_type, legacy_text in STUB_TEMPLATES.items():
        variants.append(generate_stub_hypothesis(issue_type))
        if include_legacy:
            variants.append(legacy_text)
    return list(dict.fromkeys(variants))


def analyze_funnel_with_ai(funnel_name, step_metrics, overall_conversion, cohort_name=None):
    """
    Анализирует воронку конверсии и генерирует рекомендации по улучшению
    
    Args:
        funnel_name: Название воронки
        step_metrics: Список метрик по шагам [{'step_name': ..., 'conversion_from_prev': ..., 'drop_off': ...}, ...]
        overall_conversion: Общая конверсия воронки (%)
        cohort_name: Название когорты (если анализ для конкретной когорты)
    
    Returns:
        Строка с анализом и рекомендациями
    """
    # Находим проблемные шаги (конверсия < 50%)
    problematic_steps = [
        step for step in step_metrics 
        if step.get('conversion_from_prev', 100) < 50
    ]
    
    if not problematic_steps:
        # Если нет проблемных шагов, даем общую оценку
        context = f"Воронка '{funnel_name}' показывает конверсию {overall_conversion:.1f}%."
        if cohort_name:
            context += f" Анализ для когорты '{cohort_name}'."
        context += " Все шаги имеют хорошую конверсию (>50%)."
    else:
        # Формируем контекст о проблемных шагах
        problem_desc = []
        for step in problematic_steps[:3]:  # Берем топ-3 проблемных шага
            step_name = step.get('step_name', 'Неизвестный шаг')
            conversion = step.get('conversion_from_prev', 0)
            drop_off = step.get('drop_off', 0)
            problem_desc.append(
                f"Шаг '{step_name}': конверсия {conversion:.1f}%, потеряно {drop_off} пользователей"
            )
        
        context = f"Воронка '{funnel_name}' имеет общую конверсию {overall_conversion:.1f}%.\n"
        context += f"Проблемные шаги:\n" + "\n".join(problem_desc)
        
        if cohort_name:
            context += f"\nАнализ для когорты '{cohort_name}'."
    
    prompt_content = f"""
    Ты анализируешь воронку конверсии на портале Приемной Комиссии университета.
    
    {context}
    
    Твоя задача: дать краткий анализ и конкретные рекомендации по улучшению.
    
    Формат ответа:
    - Первая строка: "Анализ:" с кратким выводом о проблеме
    - Вторая строка: "Рекомендация:" с конкретным действием для улучшения (до 140 символов)
    - Пиши на русском языке, без английских слов и транслита.
    
    Учитывай специфику:
    - Абитуриенты часто спешат и испытывают стресс
    - Формы должны быть простыми и понятными
    - Навигация должна быть интуитивной
    - Важна скорость загрузки страниц
    
    Избегай общих фраз. Давай конкретные действия: упростить форму, добавить CTA, 
    сократить количество полей, улучшить валидацию, добавить прогресс-бар и т.д.
    """
    
    system_text = """
    Ты главный UX-аналитик и специалист по конверсионной оптимизации.
    Твоя задача - находить конкретные проблемы в воронках конверсии и давать 
    практические рекомендации, которые можно сразу внедрить.
    Отвечай кратко, без воды, фокусируйся на действиях.
    """
    
    result = _send_gpt_request(system_text, prompt_content)
    
    if not result:
        # Fallback для проблемных шагов
        if problematic_steps:
            worst_step = max(problematic_steps, key=lambda x: x.get('drop_off', 0))
            step_name = worst_step.get('step_name', 'шаг')
            conversion = worst_step.get('conversion_from_prev', 0)
            return f"Анализ: Низкая конверсия на шаге '{step_name}' ({conversion:.1f}%). Рекомендация: упростить переход и добавить прогресс-индикатор, улучшить видимость следующего шага."
        else:
            return f"Анализ: Воронка работает стабильно. Рекомендация: проанализировать поведение пользователей, дошедших до конца, для дальнейшей оптимизации."
    
    return result.strip()


def analyze_version_comparison_with_ai(
    v1_name: str,
    v2_name: str,
    stats_v1: dict,
    stats_v2: dict,
    issues_diff: list,
    pages_diff: list,
    cohorts_diff: list = None,
    alerts: list = None
) -> str:
    """
    Генерирует AI-анализ сравнения двух версий продукта
    
    Args:
        v1_name: Название первой версии
        v2_name: Название второй версии
        stats_v1: Статистика первой версии {'visits': ..., 'bounce': ..., 'duration': ...}
        stats_v2: Статистика второй версии {'visits': ..., 'bounce': ..., 'duration': ...}
        issues_diff: Список изменений issues [{'status': 'new'|'worse'|'improved'|'resolved', 'issue': UXIssue, ...}, ...]
        pages_diff: Список изменений страниц [{'status': 'new'|'changed'|'removed', 'v1': PageMetrics, 'v2': PageMetrics, ...}, ...]
        cohorts_diff: Список изменений когорт (опционально)
        alerts: Список алертов (опционально)
    
    Returns:
        Строка с AI-анализом сравнения
    """
    from analytics.utils import get_readable_page_name
    
    # Формируем контекст для AI
    context_parts = []
    
    # Основные метрики
    v1_visits = stats_v1.get('visits', 0) or 0
    v2_visits = stats_v2.get('visits', 0) or 0
    v1_bounce = (stats_v1.get('bounce', 0) or 0) * 100
    v2_bounce = (stats_v2.get('bounce', 0) or 0) * 100
    v1_duration = stats_v1.get('duration', 0) or 0
    v2_duration = stats_v2.get('duration', 0) or 0
    
    visits_diff = v2_visits - v1_visits
    visits_diff_pct = (visits_diff / v1_visits * 100) if v1_visits > 0 else 0
    bounce_diff = v2_bounce - v1_bounce
    duration_diff = v2_duration - v1_duration
    
    context_parts.append(f"Сравнение версий: {v1_name} → {v2_name}")
    context_parts.append("")
    context_parts.append("Основные метрики:")
    context_parts.append(f"  Посещения: {v1_visits} → {v2_visits} ({visits_diff:+.0f}, {visits_diff_pct:+.1f}%)")
    context_parts.append(f"  Отказы: {v1_bounce:.1f}% → {v2_bounce:.1f}% ({bounce_diff:+.1f}%)")
    context_parts.append(f"  Время на сайте: {v1_duration:.1f}с → {v2_duration:.1f}с ({duration_diff:+.1f}с)")
    
    # Анализ issues
    new_issues = [i for i in issues_diff if i.get('status') == 'new']
    worse_issues = [i for i in issues_diff if i.get('status') == 'worse']
    improved_issues = [i for i in issues_diff if i.get('status') == 'improved']
    resolved_issues = [i for i in issues_diff if i.get('status') == 'resolved']
    
    if new_issues or worse_issues or improved_issues or resolved_issues:
        context_parts.append("")
        context_parts.append("Изменения в UX-проблемах:")
        if new_issues:
            context_parts.append(f"  Новых проблем: {len(new_issues)}")
            # Топ-3 новых проблем
            top_new = sorted(new_issues, key=lambda x: getattr(x.get('issue'), 'impact_score', 0) if hasattr(x.get('issue'), 'impact_score') else 0, reverse=True)[:3]
            for item in top_new:
                issue = item.get('issue')
                if issue and hasattr(issue, 'impact_score'):
                    location = get_readable_page_name(issue.location_url) if hasattr(issue, 'location_url') else 'неизвестно'
                    context_parts.append(f"    - {issue.issue_type} на {location} (impact: {issue.impact_score})")
        if worse_issues:
            context_parts.append(f"  Ухудшилось: {len(worse_issues)}")
        if improved_issues:
            context_parts.append(f"  Улучшилось: {len(improved_issues)}")
        if resolved_issues:
            context_parts.append(f"  Решено: {len(resolved_issues)}")
    
    # Анализ страниц
    changed_pages = [p for p in pages_diff if p.get('status') in ['new', 'changed']]
    if changed_pages:
        context_parts.append("")
        context_parts.append("Изменения в страницах:")
        # Топ-3 измененных страниц
        top_changed = sorted(changed_pages, key=lambda x: abs(x.get('exit_diff', 0)) + abs(x.get('time_diff', 0)), reverse=True)[:3]
        for page in top_changed:
            readable = page.get('readable', 'Неизвестная страница')
            exit_diff = page.get('exit_diff', 0)
            time_diff = page.get('time_diff', 0)
            context_parts.append(f"    - {readable}: exit_rate {exit_diff:+.1f}%, время {time_diff:+.1f}с")
    
    # Анализ когорт
    if cohorts_diff:
        new_cohorts = [c for c in cohorts_diff if c.get('status') == 'new']
        changed_cohorts = [c for c in cohorts_diff if c.get('status') == 'changed']
        if new_cohorts or changed_cohorts:
            context_parts.append("")
            context_parts.append("Изменения в когортах:")
            if new_cohorts:
                context_parts.append(f"  Новых когорт: {len(new_cohorts)}")
            if changed_cohorts:
                context_parts.append(f"  Изменившихся когорт: {len(changed_cohorts)}")
    
    # Алерты
    if alerts:
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        if critical_alerts:
            context_parts.append("")
            context_parts.append("Критические алерты:")
            for alert in critical_alerts[:3]:
                context_parts.append(f"    - {alert.get('message', '')}")
    
    full_context = "\n".join(context_parts)
    
    prompt_content = f"""
    Ты анализируешь сравнение двух версий портала Приемной Комиссии университета.
    
    {full_context}
    
    Твоя задача: дать краткий executive summary сравнения версий.
    
    Формат ответа (строго):
    - Первая строка: "Резюме:" с кратким выводом (1-2 предложения) - что изменилось в целом
    - Вторая строка: "Улучшения:" с перечислением позитивных изменений (если есть)
    - Третья строка: "Проблемы:" с перечислением негативных изменений или новых проблем (если есть)
    - Четвертая строка: "Рекомендация:" с одной конкретной рекомендацией по приоритетному действию (до 120 символов)
    
    Правила:
    - Без вступлений и общих фраз
    - Фокусируйся на значимых изменениях (отказы ±5%, время ±10%, новые критические проблемы)
    - Если изменений мало - скажи что версия стабильна
    - Рекомендация должна быть конкретной и actionable
    - Учитывай специфику приемной комиссии (абитуриенты, формы, списки)
    """
    
    system_text = """
    Ты главный продукт-аналитик портала Приемной Комиссии университета.
    Твоя задача - анализировать изменения между версиями продукта и давать 
    краткие, но информативные executive summary для менеджмента.
    Отвечай структурированно, выделяй самое важное, давай конкретные рекомендации.
    """
    
    result = _send_gpt_request(system_text, prompt_content)
    
    if not result or not result.strip():
        # Fallback анализ (используем уже вычисленные переменные)
        summary_parts = []
        
        # Определяем общий тренд
        if bounce_diff < -2 and duration_diff > 5:
            summary = f"Версия {v2_name} показывает улучшение - снижение отказов на {abs(bounce_diff):.1f}% и увеличение времени на сайте."
        elif bounce_diff > 2 and duration_diff < -5:
            summary = f"Версия {v2_name} показывает ухудшение - рост отказов на {bounce_diff:.1f}% и снижение времени на сайте."
        elif len(new_issues) > 5 or len(worse_issues) > 3:
            summary = f"Версия {v2_name} имеет больше UX-проблем - {len(new_issues)} новых и {len(worse_issues)} ухудшившихся."
        elif len(improved_issues) > 3 or len(resolved_issues) > 5:
            summary = f"Версия {v2_name} показывает улучшение - {len(improved_issues)} проблем улучшилось, {len(resolved_issues)} решено."
        else:
            summary = f"Версия {v2_name} показывает стабильные метрики с минимальными изменениями."
        
        summary_parts.append(f"Резюме: {summary}")
        
        improvements = []
        if bounce_diff < -2:
            improvements.append(f"снижение отказов на {abs(bounce_diff):.1f}%")
        if duration_diff > 5:
            improvements.append(f"увеличение времени на сайте на {duration_diff:.1f}с")
        if len(improved_issues) > 0:
            improvements.append(f"{len(improved_issues)} проблем улучшилось")
        if len(resolved_issues) > 0:
            improvements.append(f"{len(resolved_issues)} проблем решено")
        
        problems = []
        if bounce_diff > 2:
            problems.append(f"рост отказов на {bounce_diff:.1f}%")
        if duration_diff < -5:
            problems.append(f"снижение времени на сайте на {abs(duration_diff):.1f}с")
        if len(new_issues) > 0:
            problems.append(f"{len(new_issues)} новых проблем")
        if len(worse_issues) > 0:
            problems.append(f"{len(worse_issues)} проблем ухудшилось")
        
        summary_parts.append(f"Улучшения: {', '.join(improvements) if improvements else 'минимальные'}")
        summary_parts.append(f"Проблемы: {', '.join(problems) if problems else 'критических не выявлено'}")
        
        # Рекомендация
        if len(new_issues) > 5 or len(worse_issues) > 3:
            recommendation = "Приоритет: исправить критические UX-проблемы, особенно на страницах с высоким трафиком."
        elif bounce_diff > 3:
            recommendation = "Приоритет: оптимизировать страницы входа и улучшить соответствие контента ожиданиям пользователей."
        elif len(improved_issues) > 0:
            recommendation = "Продолжить работу по улучшению UX, фокусируясь на проблемах с высоким impact_score."
        else:
            recommendation = "Версия стабильна, рекомендуется мониторинг метрик и профилактика новых проблем."
        
        summary_parts.append(f"Рекомендация: {recommendation}")
        
        fallback_result = "\n".join(summary_parts)
        # Убеждаемся, что fallback всегда возвращает непустую строку
        return fallback_result if fallback_result.strip() else f"Резюме: Версия {v2_name} показывает стабильные метрики. Улучшения: минимальные. Проблемы: критических не выявлено. Рекомендация: продолжить мониторинг."
    
    # Убеждаемся, что результат не пустой
    if result and result.strip():
        return result.strip()
    else:
        # Если AI вернул пустой результат, используем fallback
        # (переменные bounce_diff, duration_diff и т.д. уже вычислены выше)
        summary_parts = []
        if bounce_diff < -2 and duration_diff > 5:
            summary = f"Версия {v2_name} показывает улучшение - снижение отказов на {abs(bounce_diff):.1f}% и увеличение времени на сайте."
        elif bounce_diff > 2 and duration_diff < -5:
            summary = f"Версия {v2_name} показывает ухудшение - рост отказов на {bounce_diff:.1f}% и снижение времени на сайте."
        else:
            summary = f"Версия {v2_name} показывает стабильные метрики с минимальными изменениями."
        summary_parts.append(f"Резюме: {summary}")
        summary_parts.append(f"Улучшения: {'снижение отказов' if bounce_diff < -2 else 'минимальные'}")
        summary_parts.append(f"Проблемы: {'критических не выявлено' if bounce_diff <= 2 else 'требуется внимание'}")
        summary_parts.append(f"Рекомендация: продолжить мониторинг метрик.")
        return "\n".join(summary_parts)
