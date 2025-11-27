import os
try:
    from gigachat import GigaChat
except ImportError:
    GigaChat = None

# Получаем креды из ENV
# Для GigaChat нужен токен авторизации (обычно base64 "Client_ID:Client_Secret" или готовый access token)
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS") 

def analyze_issue_with_ai(issue_type, location, metrics_context):
    """
    Отправляет запрос в GigaChat для генерации гипотезы.
    """
    # Если библиотеки нет, ключа нет или это заглушка - возвращаем стаб
    if not GIGACHAT_CREDENTIALS or not GigaChat:
        return generate_stub_hypothesis(issue_type)

    prompt = f"""
    Ты профессиональный UX-аналитик.
    Проанализируй проблему на сайте.
    
    Тип проблемы: {issue_type}
    Страница: {location}
    Данные: {metrics_context}
    
    Напиши кратко:
    1. Возможная причина (Гипотеза).
    2. Рекомендация по исправлению.
    """

    try:
        # verify_ssl_certs=False часто нужен в корпоративных сетях или если проблемы с сертификатами Минцифры
        with GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False) as giga:
            response = giga.chat(prompt)
            return response.choices[0].message.content
    except Exception as e:
        print(f"GigaChat Error: {e}")
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

