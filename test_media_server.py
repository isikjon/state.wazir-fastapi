#!/usr/bin/env python3
"""
Тестирование медиа-сервера для nginx конфигурации
"""

import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Отключаем предупреждения SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def test_ping():
    """Тест ping медиа-сервера"""
    print("🔍 Тестирование ping медиа-сервера...")
    
    try:
        url = "https://wazir.kg/state/upload.php?ping"
        print(f"📡 Запрос к: {url}")
        
        response = requests.get(url, verify=False, timeout=10)
        
        print(f"📊 Статус ответа: {response.status_code}")
        print(f"📦 Заголовки ответа:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ JSON ответ получен:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return True, data
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка декодирования JSON: {e}")
                print(f"📝 Ответ сервера: {response.text[:500]}")
                return False, None
        else:
            print(f"❌ Неуспешный статус: {response.status_code}")
            print(f"📝 Ответ сервера: {response.text[:500]}")
            return False, None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False, None

def test_cors_headers():
    """Тест CORS заголовков"""
    print("\n🔍 Тестирование CORS заголовков...")
    
    try:
        url = "https://wazir.kg/state/upload.php?ping"
        
        # OPTIONS запрос
        print("📡 Отправка OPTIONS запроса...")
        options_response = requests.options(url, verify=False, timeout=10)
        
        print(f"📊 OPTIONS статус: {options_response.status_code}")
        
        cors_headers = {
            'Access-Control-Allow-Origin': options_response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': options_response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': options_response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Max-Age': options_response.headers.get('Access-Control-Max-Age')
        }
        
        print("🔧 CORS заголовки:")
        for key, value in cors_headers.items():
            if value:
                print(f"   ✅ {key}: {value}")
            else:
                print(f"   ❌ {key}: НЕ НАЙДЕН")
        
        # Проверяем дублирование
        origin_headers = [key for key in options_response.headers.keys() if 'access-control-allow-origin' in key.lower()]
        if len(origin_headers) > 1:
            print(f"⚠️  ВНИМАНИЕ: Обнаружено дублирование CORS заголовков: {origin_headers}")
        else:
            print("✅ CORS заголовки не дублируются")
            
        return options_response.status_code in [200, 204]
        
    except Exception as e:
        print(f"❌ Ошибка CORS теста: {e}")
        return False

def test_file_upload_simulation():
    """Симуляция загрузки файла"""
    print("\n🔍 Симуляция загрузки файла...")
    
    try:
        url = "https://wazir.kg/state/upload.php"
        
        # Создаем фиктивные данные
        data = {
            'property_id': 'test-123',
            'panorama_type': 'true'
        }
        
        # Простой POST запрос без файлов (должен вернуть ошибку, но статус 200)
        print("📡 Отправка POST запроса без файлов...")
        response = requests.post(url, data=data, verify=False, timeout=10)
        
        print(f"📊 Статус ответа: {response.status_code}")
        print(f"📦 Заголовки ответа:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower():
                print(f"   {key}: {value}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ JSON ответ получен:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                if result.get('status') == 'error' and 'files' in result.get('message', ''):
                    print("✅ Сервер корректно обработал запрос без файлов")
                    return True
                else:
                    print("⚠️  Неожиданный ответ сервера")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка декодирования JSON: {e}")
                print(f"📝 Ответ сервера: {response.text[:500]}")
                return False
        else:
            print(f"❌ Неуспешный статус: {response.status_code}")
            print(f"📝 Ответ сервера: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка симуляции загрузки: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования медиа-сервера (nginx версия)")
    print("=" * 60)
    
    results = {}
    
    # Тест 1: Ping
    success, data = test_ping()
    results['ping'] = success
    
    if success and data:
        print(f"\n📋 Информация о сервере:")
        print(f"   Версия: {data.get('version', 'неизвестно')}")
        print(f"   Web-сервер: {data.get('web_server', 'неизвестно')}")
        print(f"   PHP версия: {data.get('php_version', 'неизвестно')}")
        print(f"   GD включен: {data.get('gd_enabled', 'неизвестно')}")
        print(f"   WebP поддержка: {data.get('webp_support', 'неизвестно')}")
    
    # Тест 2: CORS заголовки
    results['cors'] = test_cors_headers()
    
    # Тест 3: Симуляция загрузки
    results['upload_simulation'] = test_file_upload_simulation()
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    for test_name, success in results.items():
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"   {test_name.upper()}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 Все тесты пройдены! Медиа-сервер готов к работе.")
    else:
        print("\n⚠️  Некоторые тесты провалены. Требуется дополнительная настройка.")
        
        if not results.get('ping'):
            print("   • Проверьте, что upload.php содержит новый код для nginx")
        if not results.get('cors'):
            print("   • Проверьте настройки CORS в nginx конфигурации")
        if not results.get('upload_simulation'):
            print("   • Проверьте обработку POST запросов и PHP настройки")
    
    return all_passed

if __name__ == "__main__":
    main() 