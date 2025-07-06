# Гайд з оновлення Custom Open WebUI

## Автоматичне оновлення

### 1. Створіть скрипт оновлення

```bash
#!/bin/bash
# update-custom-webui.sh

echo "🔄 Starting Open WebUI update..."

# 1. Оновіть базовий образ
echo "📥 Pulling latest Open WebUI..."
docker pull ghcr.io/open-webui/open-webui:latest

# 2. Перебудуйте ваш custom образ
echo "🔨 Rebuilding custom image..."
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui
docker build -f Dockerfile.local-assets -t xynthorai-open-webui:xynthor . --no-cache

# 3. Створіть backup тег старої версії
echo "💾 Creating backup..."
docker tag xynthorai-open-webui:simple xynthorai-open-webui:backup-$(date +%Y%m%d)

# 4. Перезапустіть сервіс
echo "🚀 Restarting service..."
cd /Users/admin_pro/_Web/xynthorai-system
docker-compose stop open-webui
docker-compose up -d open-webui

echo "✅ Update complete!"
```

### 2. Зробіть скрипт виконуваним

```bash
chmod +x update-custom-webui.sh
```

## Ручне оновлення (крок за кроком)

### 1. Перевірте наявність оновлень

```bash
# Перевірте поточну версію
docker inspect xynthorai-open-webui:simple | grep "org.opencontainers.image.version"

# Перевірте останню версію upstream
docker pull ghcr.io/open-webui/open-webui:latest
```

### 2. Синхронізуйте ваш форк з upstream

```bash
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui

# Fetch останні зміни
git fetch upstream

# Перегляньте що нового
git log upstream/main --oneline -10

# Merge якщо потрібно (обережно!)
git merge upstream/main
```

### 3. Перебудуйте образ

```bash
# З кешем (швидше)
docker build -f Dockerfile.local-assets -t xynthorai-open-webui:xynthor .

# Без кешу (повне оновлення)
docker build -f Dockerfile.local-assets -t xynthorai-open-webui:xynthor . --no-cache
```

### 4. Backup старої версії

```bash
# Створіть backup тег
docker tag xynthorai-open-webui:simple xynthorai-open-webui:backup-$(date +%Y%m%d-%H%M%S)

# Або збережіть образ у файл
docker save xynthorai-open-webui:simple | gzip > backup-openwebui-$(date +%Y%m%d).tar.gz
```

### 5. Оновіть running контейнер

```bash
cd /Users/admin_pro/_Web/xynthorai-system

# Безпечне оновлення
docker-compose stop open-webui
docker-compose rm open-webui
docker-compose up -d open-webui

# Перевірте логи
docker-compose logs -f open-webui
```

## Версіонування

### Рекомендована схема тегів

```bash
# Production версії
docker tag xynthorai-open-webui:simple xynthorai-open-webui:v1.0.0
docker tag xynthorai-open-webui:simple xynthorai-open-webui:latest

# Staging версії
docker tag xynthorai-open-webui:simple xynthorai-open-webui:staging

# По датах
docker tag xynthorai-open-webui:simple xynthorai-open-webui:2024.06.27
```

### Використання в docker-compose.yml

```yaml
open-webui:
  # Використовуйте конкретну версію
  image: xynthorai-open-webui:v1.0.0
  
  # АБО latest (автооновлення)
  image: xynthorai-open-webui:latest
```

## Автоматизація через GitHub Actions

Створіть `.github/workflows/update-check.yml` у вашому форку:

```yaml
name: Check for Updates

on:
  schedule:
    - cron: '0 2 * * MON'  # Щопонеділка о 2:00
  workflow_dispatch:

jobs:
  check-updates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check upstream
        run: |
          git remote add upstream https://github.com/open-webui/open-webui.git
          git fetch upstream
          
          # Порівняти версії
          UPSTREAM_VERSION=$(git describe --tags upstream/main)
          CURRENT_VERSION=$(git describe --tags)
          
          if [ "$UPSTREAM_VERSION" != "$CURRENT_VERSION" ]; then
            echo "New version available: $UPSTREAM_VERSION"
            echo "CREATE_ISSUE=true" >> $GITHUB_ENV
          fi
      
      - name: Create issue
        if: env.CREATE_ISSUE == 'true'
        uses: actions/create-issue@v2
        with:
          title: "🔄 New Open WebUI version available"
          body: "Check and update custom build"
```

## Rollback процедура

### Якщо щось пішло не так:

```bash
# 1. Список доступних backup версій
docker images | grep xynthorai-open-webui

# 2. Повернутись на попередню версію
docker tag xynthorai-open-webui:backup-20240627 xynthorai-open-webui:simple

# 3. Перезапустити
cd /Users/admin_pro/_Web/xynthorai-system
docker-compose restart open-webui

# 4. АБО відновити з файлу
docker load < backup-openwebui-20240627.tar.gz
```

## Моніторинг оновлень

### 1. Підпишіться на releases
- https://github.com/open-webui/open-webui/releases
- Натисніть "Watch" > "Custom" > "Releases"

### 2. Перевіряйте changelog
```bash
# У вашому форку
curl -s https://api.github.com/repos/open-webui/open-webui/releases/latest | jq -r '.body'
```

### 3. Security оновлення
Завжди оновлюйте при security patches:
```bash
# Перевірте CVE
docker scout cves xynthorai-open-webui:simple
```

## Best Practices

1. **Тестуйте перед production**
   ```bash
   # Спочатку в test environment
   docker run -p 8081:8080 xynthorai-open-webui:simple
   ```

2. **Документуйте зміни**
   ```bash
   # При rebuild додайте версію
   docker build -f Dockerfile.simple \
     -t xynthorai-open-webui:simple \
     --label version="1.0.1" \
     --label update_date="$(date)" \
     .
   ```

3. **Cleanup старих образів**
   ```bash
   # Видалити старі backup
   docker image prune -a --filter "label=backup=true"
   ```

## Швидкі команди

```bash
# Оновити і перезапустити (one-liner)
docker pull ghcr.io/open-webui/open-webui:latest && \
docker build -f Dockerfile.local-assets -t xynthorai-open-webui:xynthor . && \
docker-compose restart open-webui

# Перевірити версію
docker inspect xynthorai-open-webui:simple --format '{{.Created}}'
```