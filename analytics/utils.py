import re

def get_readable_page_name(url):
    """
    Maps technical URLs to business stage names.
    """
    url = url.lower()
    
    patterns = [
        (r'/login', 'Authorization'),
        (r'/auth', 'Authorization'),
        (r'/loan/create', 'Loan Application'),
        (r'/loan/form', 'Loan Details Form'),
        (r'/mortgage', 'Mortgage Calculator'),
        (r'/card/order', 'Card Ordering'),
        (r'/profile', 'User Profile'),
        (r'/history', 'Transaction History'),
        (r'/$', 'Home Page'),
    ]
    
    for pattern, name in patterns:
        if re.search(pattern, url):
            return name
            
    # Fallback: clean up the path
    try:
        path = url.split('pfem.mai.ru')[-1].split('?')[0]
        return path if path else "Unknown Page"
    except:
        return url

def generate_ai_hypothesis(issue_type, context):
    """
    Stub for LLM generation.
    In real MVP, this would call OpenAI/GigaChat API.
    """
    prompts = {
        'RAGE_CLICK': "Гипотеза: Элемент выглядит кликабельным, но ответ задержан. Исправить: добавить ховер/лоадер и проверить JS обработчик.",
        'HIGH_BOUNCE': "Гипотеза: Первый экран не совпадает с ожиданием трафика или грузится медленно. Исправить: скорректировать H1/offer под источник и ускорить LCP.",
        'LOOPING': "Гипотеза: Пользователь теряет контекст навигации и возвращается назад. Исправить: упростить путь и добавить явный CTA/хлебные крошки.",
        'FORM_ABANDON': "Гипотеза: Слишком много полей или ранний запрос чувствительных данных. Исправить: сократить форму, разбить на шаги и показать прогресс.",
    }
    
    base_hypothesis = prompts.get(issue_type, "Гипотеза: сложный UX кейс. Исправить: провести ручной разбор и юзабилити-тест.")
    
    return f"[AI Generated] {base_hypothesis} (Данные: {context})"
