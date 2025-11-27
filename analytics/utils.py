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
        'RAGE_CLICK': "Users are frustrated because the element looks interactive but isn't responding quickly. It might be a slow API call or a broken JS handler.",
        'HIGH_BOUNCE': "The page content doesn't match user expectations from the traffic source, or the load time is too high.",
        'LOOPING': "The navigation structure is confusing. Users are going back and forth trying to find a specific feature that isn't clearly labeled.",
        'FORM_ABANDON': "The form is likely too long or asks for sensitive information too early. Validation errors might be unclear."
    }
    
    base_hypothesis = prompts.get(issue_type, "Complex UX anomaly detected requiring manual review.")
    
    return f"[AI Generated] {base_hypothesis} (Context: {context})"

