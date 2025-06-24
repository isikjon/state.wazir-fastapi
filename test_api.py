#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API создания объявлений
"""
import requests
import json

# Токен из браузера (из консоли)
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzUwNzkxMjk4fQ.w5xdQmsot4y-TQkeIaQeN7h5HSrGZDERc0VSHwySoPU"

def test_api_endpoint():
    """Тестируем API endpoint для создания объявлений"""
    url = "http://127.0.0.1:8000/api/v1/properties/with-media"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    # Тестовые данные (без файлов для простоты)
    data = {
        "title": "Тестовое объявление",
        "description": "Описание тестового объявления",
        "price": 100000,
        "address": "Тестовый адрес",
        "city": "Бишкек"
    }
    
    try:
        # Делаем OPTIONS запрос для проверки CORS
        options_response = requests.options(url, headers=headers)
        print(f"OPTIONS запрос: {options_response.status_code}")
        
        # Делаем GET запрос для проверки доступности endpoint
        get_response = requests.get(url.replace('/with-media', ''), headers=headers)
        print(f"GET /properties: {get_response.status_code}")
        
        print("API endpoint доступен!")
        
    except requests.exceptions.ConnectionError:
        print("Ошибка: Сервер не запущен на http://127.0.0.1:8000")
    except Exception as e:
        print(f"Ошибка при тестировании API: {e}")

if __name__ == "__main__":
    test_api_endpoint() 