import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

try:
    from analytics.ai_service import analyze_issue_with_ai
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from analytics.ai_service import analyze_issue_with_ai

def test_ai():
    print("Testing Yandex AI integration...")
    
    # Тестовые данные
    issue_type = "HIGH_BOUNCE"
    location = "/landing-page"
    metrics_context = "Bounce rate 85%, Avg session duration 10s"

    print(f"Sending request for: {issue_type} at {location}")
    
    # Вызов функции
    result = analyze_issue_with_ai(issue_type, location, metrics_context)
    
    print("-" * 50)
    print("AI Response:")
    print(result)
    print("-" * 50)

if __name__ == "__main__":
    test_ai()

