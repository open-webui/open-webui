
# Geomas 👋



# Гайд по запуску

Запуск системы(пока что) осуществляется изнутри докер контейнера

Позже, мы сделаем рабочий docker-compose, но сейчас это нерелевантно

**+++ ВАЖНО! ACHTUNG! IMPORTANT! +++**

Все наши данные, чаты, агенты и тд хранятся в папке backend/data. Каждые пару недель я делаю бэкап и складываю их сюда:

https://drive.google.com/drive/folders/1AaqxuBb3apJe7sqTJdjgD8kkP_e3RLyP?usp=sharing

Они большие и в гит не лезут. 

Если перед запуском проекта не скопировать папку *data* в backend, то никаких наших данных не будет.

**+++ Конец важной секции +++**

1) Создать контейнер
```
docker run -it --name balabanov_open_web --net=host -v /home/balabanov/:/home/ python:3.10 bash -f
```
В целом примаунтить надо лишь папку с data чтобы туда скопировать ее. Но если не хотите маунтить:

```
docker run -it --name balabanov_open_web --net=host python:3.10 bash -f

docker cp <path to data> container_name:<path to data>

```

2) Склонировать репозиторий

```
git clone git@github.com:data-satanism/open-webui-geo.git
```

3) Войти в него

```
cd open-webui-geo
```

4) Скопируйте папку **data** в **backend**
5) Подготовка:

```
cd backend
python3.10 -m venv venv
./venv/bin/python3.10 -m pip install -r requirements.txt

echo $(head -c 12 /dev/random | base64) > .webui_secret_key
export PORT=8000
export HOST=212.41.21.72

```
6) Запуск
Есть несколько вариантов запуска. Для запуска в бэкграунде юзайте команду screen

Гайд по ней - https://internet-lab.ru/linux_screen

Тестовый запуск
```
PYTHONPATH=. WEBUI_SECRET_KEY=$(cat .webui_secret_key)  ./venv/bin/python3.10 -m uvicorn open_webui.main:app --host=212.41.21.72 --port 8503 --reload
```



Запуск с логгингом
```
export PYTHONPATH=. && export WEBUI_SECRET_KEY=$(cat .webui_secret_key) && export PYTHONUNBUFFERED=1 && exec ./venv/bin/python3.10 -u -m uvicorn open_webui.main:app --host 212.41.21.72 --port 8503 --reload > webui.log 2>&1

```