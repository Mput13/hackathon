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
                {"role": "system", "content": "Ты главный UX-аналитик в финтех-команде. Отвечай четко, по делу, без воды."},
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
        'RAGE_CLICK': "Гипотеза: Клик по элементу без отклика или долгая загрузка. Исправить: добавить явный ховер/спиннер и проверить обработчик клика.",
        'HIGH_BOUNCE': "Гипотеза: Первый экран не совпадает с ожиданием трафика или грузится медленно. Исправить: обновить H1/hero под источник и оптимизировать LCP.",
        'LOOPING': "Гипотеза: Пользователь не находит целевое действие и ходит по одному пути. Исправить: упростить путь и добавить заметный CTA.",
        'FORM_ABANDON': "Гипотеза: Слишком много полей или ранний запрос чувствительных данных. Исправить: сократить форму и разделить на шаги с прогрессом."
    }
    return stubs.get(issue_type, "Рекомендуется детальный анализ поведения пользователя.")
