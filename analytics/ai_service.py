import os
import sys
import requests
import json

# Получаем креды из ENV
FOLDER_ID = os.environ.get("FOLDER_ID") or os.environ.get("folder_id")
API_KEY = os.environ.get("API_KEY") or os.environ.get("api_key")

def analyze_issue_with_ai(issue_type, location, metrics_context):
    """
    Отправляет запрос в Yandex Foundation Models (YandexGPT) через REST API.
    """
    if not FOLDER_ID or not API_KEY:
        # print("DEBUG: Missing FOLDER_ID or API_KEY")
        return generate_stub_hypothesis(issue_type)

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

    # URL для синхронного режима (completion)
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {API_KEY}", # ВАЖНО: Api-Key, а не Bearer
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
                "text": "Ты главный UX-аналитик в финтех-команде. Отвечай четко, по делу, без воды."
            },
            {
                "role": "user",
                "text": prompt_content
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        
        if response.status_code != 200:
            print(f"YandexAI Error: Status {response.status_code}, Body: {response.text}")
            return generate_stub_hypothesis(issue_type)
            
        result = response.json()
        # Структура ответа YandexGPT: result -> alternatives -> [ { message: { text: ... } } ]
        text = result['result']['alternatives'][0]['message']['text']
        return text

    except Exception as e:
        print(f"YandexAI Exception: {e}")
        return generate_stub_hypothesis(issue_type)

def generate_stub_hypothesis(issue_type):
    """Резервные тексты, если AI недоступен"""
    stubs = {
        'RAGE_CLICK': "Гипотеза: Клик по элементу без отклика или долгая загрузка. Исправить: добавить явный ховер/спиннер и проверить обработчик клика.",
        'HIGH_BOUNCE': "Гипотеза: Первый экран не совпадает с ожиданием трафика или грузится медленно. Исправить: обновить H1/hero под источник и оптимизировать LCP.",
        'LOOPING': "Гипотеза: Пользователь не находит целевое действие и ходит по одному пути. Исправить: упростить путь и добавить заметный CTA.",
        'FORM_ABANDON': "Гипотеза: Слишком много полей или ранний запрос чувствительных данных. Исправить: сократить форму и разделить на шаги с прогрессом."
    }
    return stubs.get(issue_type, "Рекомендуется детальный анализ поведения пользователя.")
