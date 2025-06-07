#!/bin/bash

# Скрипт для быстрого деплоя изменений (2-3 секунды)

echo "🚀 Быстрый деплой изменений..."

# Проверяем, запущен ли контейнер
if [ "$(docker ps -q -f name=statewazir-fastapi-web-1)" ]; then
    echo "📦 Перезапускаем контейнер без пересборки..."
    docker-compose restart web
    echo "✅ Готово! Изменения применены за $(date +'%S') секунд"
else
    echo "⚠️  Контейнер не запущен. Запускаем..."
    docker-compose up -d
    echo "✅ Контейнер запущен!"
fi

echo "🌐 Приложение доступно по адресу: http://localhost:8000" 