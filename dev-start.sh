#!/bin/bash

# Скрипт для запуска OpenWebUI в режиме разработки
# Использует docker-compose-garik.yaml для сборки из локального кода

echo "🚀 Запуск OpenWebUI в режиме разработки..."

# Останавливаем существующие контейнеры
echo "⏹️  Останавливаем существующие контейнеры..."
docker-compose -f docker-compose-garik.yaml down

# Пересобираем образ с последними изменениями
echo "🔨 Пересобираем образ OpenWebUI с Dockerfile.dev..."
docker-compose -f docker-compose-garik.yaml build --no-cache openwebui

# Запускаем сервисы
echo "▶️  Запускаем сервисы..."
docker-compose -f docker-compose-garik.yaml up -d

echo "✅ Готово! OpenWebUI доступен по адресу: http://localhost:3000"
echo "📝 Для просмотра логов: docker-compose -f docker-compose-garik.yaml logs -f openwebui"
echo "🛑 Для остановки: docker-compose -f docker-compose-garik.yaml down"
