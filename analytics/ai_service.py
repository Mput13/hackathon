import os
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Получаем креды из ENV
FOLDER_ID = os.environ.get("folder_id")
API_KEY = os.environ.get("api_key")

def analyze_issue_with_ai(issue_type, location, metrics_context):
    """
    Отправляет запрос в Yandex AI (через OpenAI client) для генерации гипотезы.
    """
    # Если библиотеки нет, ключа нет или это заглушка - возвращаем стаб
    if not OpenAI or not FOLDER_ID or not API_KEY:
        return generate_stub_hypothesis(issue_type)

    prompt_content = f"""
    Проанализируй проблему на сайте.
    
    Тип проблемы: {issue_type}
    Страница: {location}
    Данные: {metrics_context}
    
    Напиши кратко:
    1. Возможная причина (Гипотеза).
    2. Рекомендация по исправлению.
    """

    model = f"gpt://{FOLDER_ID}/qwen3-235b-a22b-fp8/latest"

    try:
        client = OpenAI(
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            api_key=API_KEY,
            project=FOLDER_ID,
        )
        
        # Используем chat.completions.create (стандартный метод OpenAI)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты - полезный ассистент. Ты профессиональный UX-аналитик."},
                {"role": "user", "content": prompt_content}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"YandexAI Error: {e}")
        return generate_stub_hypothesis(issue_type)

def generate_stub_hypothesis(issue_type):
    """Резервные тексты, если AI недоступен"""
    stubs = {
        'RAGE_CLICK': "Гипотеза: Пользователь ожидает реакции интерфейса, но она задерживается. Решение: Проверить время ответа API и добавить индикатор загрузки.",
        'HIGH_BOUNCE': "Гипотеза: Контент первого экрана не соответствует ожиданиям из источника трафика. Решение: Скорректировать заголовки H1.",
        'LOOPING': "Гипотеза: Пользователь потерял контекст навигации. Решение: Упростить структуру меню.",
        'FORM_ABANDON': "Гипотеза: Форма содержит избыточные поля. Решение: Внедрить прогрессивное заполнение."
    }
    return stubs.get(issue_type, "Рекомендуется детальный анализ поведения пользователя.")
