# Список ритуалов для апдейта на новую версию

1. В `src/lib/constants.ts`:
   Поменять 
   ```ts
   export const APP_NAME = 'Geomas';
   ```

2. В `backend/open_webui/env.py` (примерно строка 93):

   Изменить на:

   ```py
   WEBUI_NAME = os.environ.get("WEBUI_NAME", "Geomas")
   ```
   И в следующей строке убрать автоизменение имени, иначе система откатит изменения 
   Удалить или закомментировать:

   ```py
   if WEBUI_NAME != "Open WebUI":
       WEBUI_NAME += " (Open WebUI)"
   ```
   и там же 

   ```py
    CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE = 20
   ```

3. В `backend/open_webui/retrieval/loaders/mistral.py`:

   Поставить таймаут `3600` секунд в конструкторе класса - иначе OCR будет падать на больших файлах 

4. Обновить зависимости(пока что не нужно, оставил на будущее, если оно поломоется):

   ```bash
   pip install strenum
   ```

5. В `backend/open_webui/utils/plugin.py`:

   Добавить `return` в начале двух последних функций.
   Отключает автоапдейт некоторых пакетов, иначе система будет вместо запуска пытаться установить пакеты 

6. В `backend/open_webui/retrieval/vector/type.py`:
    Пока тоже не нужно
   ```py
   try:
       from enum import StrEnum  # Python 3.11+
   except ImportError:
       from strenum import StrEnum  # Backport for older Python
   ```

7. Заменить изображения в на изображения из папки в backend:

   - `static/`
   - `static/static`
   - `backend/open_webui/static`

   И заменить `Open WebUI` на `Geomas` в `index.html`.

8. Выполнить сборку фронтенда:
   yarn предпочтительнее npm

   ```bash
   yarn install
   yarn add @internationalized/date
   yarn run build
   ```

9. Убрать в `backend/open_webui/utils/tools.py`:

    - `view_file`
    - `view_knowledge_file`

## Обряды запуска

Необязательно - если в контейнере, где уже есть все зависимости
```bash
cd backend
python3.10 -m venv venv
./venv/bin/python3.10 -m pip install -r requirements.txt
```

ВСЕГДА ГЕНЕРИРОВАТЬ КЛЮЧ!!
```bash
echo "$(head -c 12 /dev/random | base64)" > .webui_secret_key


Тестовые запуск
PYTHONPATH=. WEBUI_SECRET_KEY="$(cat .webui_secret_key)" ./venv/bin/python3.11 -m uvicorn open_webui.main:app --host=212.41.21.72 --port 8503 --reload


ПРОД ЗАПУСК!!
export PYTHONPATH=. && export WEBUI_SECRET_KEY="$(cat .webui_secret_key)" && export RAG_SYSTEM_CONTEXT=True && export PYTHONUNBUFFERED=1 && exec ./venv/bin/python3.11 -u -m uvicorn open_webui.main:app --host 212.41.21.72 --port 8503 --reload > webui.log 2>&1



ТЕСТ - ЗАПУСК В КОНТЕЙНЕРЕ, ПОКА НЕ ОТЛАЖЕНО СОВСЕМ
./venv/bin/python3.10 -m pip install youtube-transcript-api scholarly habanero arxiv openrouteservice pygments yfinance>=0.2.66 pandas>=2.2.0 pydantic>=2.0.0 requests>=2.28.0

docker compose -f _docker-compose.local.yml restart
docker compose -f _docker-compose.local.yml up --build
```

`// background`

**RUN INSIDE CONTAINER!!**







