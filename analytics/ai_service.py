import os
import sys
import requests
import json

# Получаем креды из ENV
FOLDER_ID = os.environ.get("FOLDER_ID") or os.environ.get("folder_id")
API_KEY = os.environ.get("API_KEY") or os.environ.get("api_key")

def _send_gpt_request(system_text, user_text):
    """Helper to send request to YandexGPT"""
    if not FOLDER_ID or not API_KEY:
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

def analyze_issue_with_ai(issue_type, location, metrics_context):
    """
    Отправляет запрос в Yandex Foundation Models (YandexGPT) через REST API.
    """
    prompt_content = f"""
    Ты разбираешь инцидент UX на банковском веб-проекте.
    Дано:
    - Тип проблемы: {issue_type}
    - Страница/URL: {location}
    - Ключевые метрики/наблюдения: {metrics_context}

    Требования к ответу:
    - Без вступлений и извинений.
    - Две строки, каждая начинается с маркера: "Гипотеза:" и "Исправить:".
    - Гипотеза: конкретная причина с привязкой к данным.
    - Исправить: одно практическое действие (UI/копирайт/поток/тех), не длиннее 140 символов.
    """
    
    system_text = "Ты главный UX-аналитик в финтех-команде. Отвечай четко, по делу, без воды."
    
    result = _send_gpt_request(system_text, prompt_content)
    return result if result else generate_stub_hypothesis(issue_type)

def generate_cohort_name(metrics_dict):
    """
    Генерирует название для когорты пользователей на основе их метрик.
    metrics_dict: {'bounce': 80.5, 'duration': 12, 'depth': 1.2, 'top_goals': '...'}
    """
    prompt_content = f"""
    Ты маркетолог-аналитик. Придумай название для сегмента пользователей веб-сайта вуза.
    Метрики сегмента:
    - Отказы (Bounce Rate): {metrics_dict.get('bounce')}%
    - Время на сайте: {metrics_dict.get('duration')} сек
    - Глубина просмотра: {metrics_dict.get('depth')} стр
    - Достигнутые цели (конверсии): {metrics_dict.get('top_goals')}
    
    Задача: Дай короткое, емкое название (2-4 слова) для этой группы, описывающее их поведение. 
    Примеры: "Случайные прохожие", "Заинтересованные абитуриенты", "Нетерпимые мобильные пользователи".
    В ответе только название, без кавычек и лишнего текста.
    """

    system_text = "Ты опытный маркетолог. Твоя задача - сегментация аудитории."
    
    result = _send_gpt_request(system_text, prompt_content)
    
    if not result:
        # Fallback name
        if metrics_dict.get('bounce', 0) > 70:
            return "High Bounce Users"
        elif metrics_dict.get('duration', 0) > 60:
            return "Engaged Users"
        else:
            return "Average Users"
            
    return result.strip().replace('"', '').replace("'", "")

def generate_stub_hypothesis(issue_type):
    """Резервные тексты, если AI недоступен"""
    stubs = {
        'RAGE_CLICK': "Гипотеза: Клик по элементу без отклика или долгая загрузка. Исправить: добавить явный ховер/спиннер и проверить обработчик клика.",
        'HIGH_BOUNCE': "Гипотеза: Первый экран не совпадает с ожиданием трафика или грузится медленно. Исправить: обновить H1/hero под источник и оптимизировать LCP.",
        'LOOPING': "Гипотеза: Пользователь не находит целевое действие и ходит по одному пути. Исправить: упростить путь и добавить заметный CTA.",
        'FORM_ABANDON': "Гипотеза: Слишком много полей или ранний запрос чувствительных данных. Исправить: сократить форму и разделить на шаги с прогрессом."
    }
    return stubs.get(issue_type, "Рекомендуется детальный анализ поведения пользователя.")
