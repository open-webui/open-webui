#!/bin/bash

# Скрипт для быстрой пересборки OpenWebUI при изменениях в коде
# Перезапускает только openwebui сервис без полной пересборки

echo "🔄 Перезапуск OpenWebUI с последними изменениями..."

# Останавливаем только openwebui
echo "⏹️  Останавливаем OpenWebUI..."
docker-compose -f docker-compose-garik.yaml stop openwebui

# Перезапускаем openwebui с новым кодом
echo "🔄 Перезапускаем OpenWebUI с обновленным кодом..."

# Запускаем openwebui
echo "▶️  Запускаем OpenWebUI..."
docker-compose -f docker-compose-garik.yaml up -d openwebui

echo "✅ Готово! OpenWebUI перезапущен с последними изменениями"
echo "📝 Для просмотра логов: docker-compose -f docker-compose-garik.yaml logs -f openwebui"
