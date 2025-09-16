# ASGOR-30: Настройка OpenWebUI для разработки

## 🎯 Цель проекта
Настроить OpenWebUI для разработки из локального кода вместо использования готового образа из Docker Hub.

## 📋 Что было сделано

### ✅ Изменения в `docker-compose-garik.yaml`:

1. **Заменил готовый образ на сборку из кода:**
   - Добавил `build` конфигурацию с использованием локального `Dockerfile`
   - Настроил аргументы для CUDA поддержки

2. **Настроил монтирование исходного кода:**
   - `./backend:/app/backend` - бэкенд код
   - `./src:/app/src` - фронтенд код  
   - `./static:/app/static` - статические файлы
   - Конфигурационные файлы (package.json, svelte.config.js и т.д.)

3. **Установил переменные для режима разработки:**
   - `ENV=dev` - режим разработки
   - `DOCKER=false` - отключение Docker-специфичных настроек

### 🛠️ Созданы скрипты для удобства:

1. **`dev-start.sh`** - полный запуск с пересборкой
2. **`dev-rebuild.sh`** - быстрая пересборка при изменениях

## 🚀 Как использовать

### Первый запуск:
```bash
./dev-start.sh
```

### При изменениях в коде:
```bash
./dev-rebuild.sh
```

### Просмотр логов:
```bash
docker-compose -f docker-compose-garik.yaml logs -f openwebui
```

### Остановка:
```bash
docker-compose -f docker-compose-garik.yaml down
```

## 🌐 Доступ к приложению

OpenWebUI будет доступен по адресу: **http://localhost:3000**

## 📁 Структура файлов

```
webui/
├── docker-compose-garik.yaml    # Конфигурация для разработки
├── dev-start.sh                 # Скрипт полного запуска
├── dev-rebuild.sh              # Скрипт быстрой пересборки
└── asgor/
    └── README.md               # Эта инструкция
```

## ⚙️ Технические детали

- **CUDA поддержка**: Включена для GPU ускорения
- **Режим разработки**: `ENV=dev`, `DOCKER=false`
- **Монтирование кода**: Все исходные файлы монтируются в контейнер
- **Ollama интеграция**: Настроена для работы с локальным Ollama

## 🔧 Troubleshooting

Если возникают проблемы:

1. **Проверьте конфигурацию:**
   ```bash
   docker-compose -f docker-compose-garik.yaml config
   ```

2. **Очистите кэш Docker:**
   ```bash
   docker system prune -a
   ```

3. **Пересоберите с нуля:**
   ```bash
   docker-compose -f docker-compose-garik.yaml build --no-cache
   ```
