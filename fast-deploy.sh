#!/bin/bash

# Супер быстрый деплой с bind mounts - мгновенные изменения!

echo "⚡ Максимально быстрый деплой с live reload..."

# Останавливаем старый контейнер если запущен
docker-compose down 2>/dev/null

# Запускаем с development конфигурацией
echo "🔄 Запускаем с live reload..."
docker-compose -f docker-compose.dev.yml up -d

echo "✅ Готово! Теперь все изменения применяются мгновенно!"
echo "📝 Редактируйте файлы - изменения подхватываются автоматически"
echo "🌐 Приложение: http://localhost:8000"

# Показываем логи для отладки
echo "📊 Логи приложения:"
docker-compose -f docker-compose.dev.yml logs -f --tail=20 