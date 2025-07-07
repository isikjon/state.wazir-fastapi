#!/bin/bash

echo "🧹 ОЧИСТКА ПРОЕКТА ОТ МУСОРНЫХ ФАЙЛОВ"
echo "====================================="

# Создаем резервную копию на всякий случай
echo "📦 Создание резервной копии..."
git add -A
git commit -m "backup before cleanup" || echo "ℹ️  Нет изменений для коммита"

echo "🗑️  Удаление мусорных файлов..."

# Удаляем дублированные файлы
echo "- Удаление дублированных файлов..."
rm -f main_backup.py
rm -f requirements_new.txt

# Удаляем тестовые файлы
echo "- Удаление тестовых файлов..."
rm -f test_*.py

# Удаляем неиспользуемые приложения
echo "- Удаление неиспользуемых приложений..."
rm -f websocket_app.py
rm -f asgi.py
rm -f run_telegram_bot.py

# Удаляем утилиты инициализации (после настройки БД они не нужны)
echo "- Удаление утилит инициализации..."
rm -f init_categories.py
rm -f init_service_categories.py
rm -f create_admin.py
rm -f create_superadmin.py
rm -f fix_property.py

# Удаляем SQL файлы (можно пересоздать из миграций)
echo "- Удаление SQL файлов..."
rm -f *.sql

# Удаляем временные JSON файлы
echo "- Удаление временных JSON файлов..."
rm -f chat_messages.json

# Удаляем пустые и мусорные файлы
echo "- Удаление пустых файлов..."
rm -f 6BmBc3r

# Удаляем дублированную структуру (оставляем api/v1/, удаляем корневые schemas/, routes/)
echo "- Удаление дублированной структуры..."
rm -rf routes/
rm -rf schemas/
rm -rf models/ # Корневая папка models дублирует app/models

# Очистка логов и временных файлов
echo "- Очистка логов и временных файлов..."
rm -rf logs/*.log 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Очистка пустых папок
echo "- Удаление пустых папок..."
find . -type d -empty -delete 2>/dev/null || true

echo "✅ Очистка завершена!"
echo ""
echo "📊 СОХРАНЕННЫЕ ВАЖНЫЕ ФАЙЛЫ:"
echo "- main.py (основное приложение)"
echo "- config.py (конфигурация)"
echo "- database.py (настройки БД)"
echo "- requirements.txt (зависимости)"
echo "- app/ (модели, сервисы, API)"
echo "- api/ (API эндпоинты)"
echo "- templates/ (HTML шаблоны)"
echo "- static/ (статические файлы)"
echo "- alembic/ (миграции БД)"
echo ""
echo "🗑️  УДАЛЕННЫЕ МУСОРНЫЕ ФАЙЛЫ:"
echo "- main_backup.py"
echo "- requirements_new.txt"
echo "- test_*.py"
echo "- websocket_app.py"
echo "- asgi.py"
echo "- run_telegram_bot.py"
echo "- init_*.py"
echo "- create_*.py"
echo "- fix_property.py"
echo "- *.sql"
echo "- chat_messages.json"
echo "- routes/"
echo "- schemas/"
echo "- models/ (корневая)"
echo "- __pycache__/"
echo "- *.pyc"
echo ""
echo "💡 Для отката изменений: git reset --hard HEAD^"
echo "💡 Проверьте работу приложения: python main.py" 