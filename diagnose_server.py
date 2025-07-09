#!/usr/bin/env python3
"""
Диагностика медиа-сервера
"""

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Отключаем SSL предупреждения
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def check_server_status():
    """Проверяем общий статус сервера"""
    print("🔍 Проверка общего статуса сервера...")
    
    try:
        # Проверяем основной домен
        response = requests.get("https://wazir.kg", verify=False, timeout=10)
        print(f"📊 Основной сайт: {response.status_code}")
        print(f"🖥️  Сервер: {response.headers.get('Server', 'Неизвестно')}")
        
        # Проверяем директорию state
        response = requests.get("https://wazir.kg/state/", verify=False, timeout=10)
        print(f"📊 /state/ директория: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def check_php_direct():
    """Прямая проверка PHP файла"""
    print("\n🔍 Прямая проверка upload.php...")
    
    try:
        url = "https://wazir.kg/state/upload.php"
        
        # Простой GET запрос без параметров
        print(f"📡 GET запрос к: {url}")
        response = requests.get(url, verify=False, timeout=10)
        
        print(f"📊 Статус: {response.status_code}")
        print(f"📦 Content-Type: {response.headers.get('Content-Type', 'Не указан')}")
        print(f"📦 Server: {response.headers.get('Server', 'Не указан')}")
        
        if response.status_code == 500:
            print("❌ Ошибка 500 - проблема с PHP кодом")
            print("📝 Ответ сервера:")
            print(response.text[:300] + "..." if len(response.text) > 300 else response.text)
        elif response.status_code == 404:
            print("❌ Файл upload.php не найден")
        elif response.status_code == 200:
            print("✅ PHP файл доступен")
            print("📝 Начало ответа:")
            print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
        
        return response.status_code
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def check_error_logs():
    """Пытаемся получить информацию об ошибках"""
    print("\n🔍 Проверка возможных ошибок...")
    
    # Проверяем разные возможные проблемы
    common_issues = [
        "Синтаксическая ошибка PHP",
        "Отсутствие прав на выполнение",
        "Неправильная nginx конфигурация",
        "Проблемы с PHP-FPM",
        "Неправильный путь к файлу"
    ]
    
    print("🚨 Возможные причины ошибки 500:")
    for i, issue in enumerate(common_issues, 1):
        print(f"   {i}. {issue}")

def main():
    """Основная диагностика"""
    print("🚀 ДИАГНОСТИКА МЕДИА-СЕРВЕРА")
    print("=" * 50)
    
    # Проверка 1: Общий статус сервера
    server_ok = check_server_status()
    
    if not server_ok:
        print("\n❌ Сервер недоступен! Проверьте подключение к интернету.")
        return
    
    # Проверка 2: PHP файл
    php_status = check_php_direct()
    
    # Проверка 3: Рекомендации
    check_error_logs()
    
    print("\n" + "=" * 50)
    print("📋 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
    
    if php_status == 500:
        print("""
🔧 ДЛЯ ИСПРАВЛЕНИЯ ОШИБКИ 500:

1. 📤 Загрузите новый файл upload.php на сервер:
   - Используйте содержимое файла: media_server_upload_simple.php
   - Сохраните как: /var/www/html/state/upload.php
   
2. 🔐 Проверьте права доступа:
   chmod 644 /var/www/html/state/upload.php
   
3. 🗂️ Создайте директорию uploads если её нет:
   mkdir -p /var/www/html/state/uploads
   chmod 755 /var/www/html/state/uploads
   
4. ⚙️ Настройка nginx - добавьте в конфигурацию:
   
   location /state/ {
       add_header 'Access-Control-Allow-Origin' '*' always;
       add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
       add_header 'Access-Control-Allow-Headers' 'Content-Type' always;
       
       if ($request_method = 'OPTIONS') {
           return 204;
       }
       
       location ~ \.php$ {
           try_files $uri =404;
           fastcgi_pass unix:/var/run/php/php5.6-fpm.sock;
           fastcgi_index index.php;
           include fastcgi_params;
           fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
           
           add_header 'Access-Control-Allow-Origin' '*' always;
       }
   }
   
5. 🔄 Перезапустите nginx:
   sudo systemctl reload nginx

6. 📊 Проверьте логи:
   tail -f /var/log/nginx/error.log
   tail -f /var/log/php5.6-fpm.log
        """)
    elif php_status == 404:
        print("\n❌ Файл upload.php не найден - загрузите его на сервер!")
    elif php_status == 200:
        print("\n✅ PHP файл работает, проверьте nginx конфигурацию для CORS")

if __name__ == "__main__":
    main() 