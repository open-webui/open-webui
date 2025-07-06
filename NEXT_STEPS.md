# Наступні кроки для інтеграції

## 1. Перевірте образ
```bash
# Образ вже створений
docker images xynthorai-open-webui:simple

# REPOSITORY       TAG       IMAGE ID       CREATED          SIZE
# xynthorai-open-webui   simple    8d10ded5b73a   11 minutes ago   6.21GB
```

## 2. Оновіть основний docker-compose.yml

Відкрийте файл: `/Users/admin_pro/_Web/xynthorai-system/docker-compose.yml`

Знайдіть секцію `open-webui:` і змініть:

```yaml
# БУЛО:
open-webui:
  image: ghcr.io/open-webui/open-webui:latest
  
# СТАНЕ:
open-webui:
  image: xynthorai-open-webui:simple
```

## 3. Перезапустіть сервіс

```bash
cd /Users/admin_pro/_Web/xynthorai-system

# Зупиніть старий
docker-compose stop open-webui

# Видаліть старий контейнер
docker-compose rm open-webui

# Запустіть новий
docker-compose up -d open-webui

# Перевірте логи
docker-compose logs -f open-webui
```

## 4. Що включено в образ

✅ **Базовий Open WebUI** - останній офіційний образ
✅ **Environment змінні**:
   - WEBUI_NAME="XYNTHOR AI"
   - XYNTHORAI_ENABLED=true
   - XYNTHORAI_MIDDLEWARE_URL=http://xynthorai-middleware:3000

⚠️ **Обмеження**: 
   - Фавікон та логотип НЕ змінені (потрібні патчі)
   - Кольори та стилі НЕ змінені (потрібні патчі)

## 5. Якщо потрібні глибші зміни

### Варіант А: Додати патчі
```bash
cd xynthorai-open-webui

# Внесіть зміни в код
# Створіть патч
git diff > patches/002-my-changes.patch

# Перебудуйте образ
docker build -f Dockerfile.simple -t xynthorai-open-webui:simple .
```

### Варіант Б: Використати volume для статичних файлів
```yaml
open-webui:
  image: xynthorai-open-webui:simple
  volumes:
    - ./custom-logo.png:/app/backend/static/logo.png
    - ./custom-styles.css:/app/backend/static/custom.css
```

## 6. Перевірка роботи

1. Відкрийте http://localhost:8080
2. Перевірте чи відображається "XYNTHOR AI" в заголовку
3. Перевірте інтеграцію з XynthorAI middleware

## Проблеми?

- **Образ не знайдено**: Перевірте `docker images`
- **Старий UI**: Очистіть кеш браузера (Ctrl+F5)
- **Помилки запуску**: Перевірте `docker-compose logs open-webui`