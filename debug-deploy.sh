#!/bin/bash

# Скрипт для деплоя с отладочными логами

echo "🐛 Деплой с отладочными логами..."

# Останавливаем старый контейнер
docker-compose down 2>/dev/null

# Запускаем с development конфигурацией
echo "🔄 Запускаем с отладкой..."
docker-compose -f docker-compose.dev.yml up -d

echo "✅ Контейнер запущен!"
echo "🌐 Приложение: http://localhost:8000"
echo "📋 Админка: http://localhost:8000/admin/requests"
echo ""
echo "📊 Показываем логи (нажмите Ctrl+C для выхода):"
echo "Ищите строки с DEBUG для диагностики проблем с изображениями"
echo "=" * 60

# Показываем логи в реальном времени с фильтрацией
docker-compose -f docker-compose.dev.yml logs -f --tail=50 | grep -E "(DEBUG|ERROR|image|photo)" 