# Customize for Alfred


### **1. Open WebUI 소스코드 다운로드**
```bash
git clone https://github.com/open-webui/open-webui.git
cd open-webui
```

### **2. Docker 컨테이너 실행 시 로컬 소스코드 마운트하기**
#### **(1) 기존 컨테이너 중지 및 삭제**
먼저 기존 컨테이너를 중지하고 삭제하자.
```bash
docker stop open-webui
docker rm open-webui
```

#### **(2) 수정 가능한 상태로 컨테이너 실행**
로컬에서 수정한 소스를 마운트하면서 컨테이너를 실행하려면 아래와 같이 `-v` 옵션을 추가하면 돼.

```bash
docker run -d -p 8080:8080 \
  -v $(pwd)/backend:/app/backend \
  -v $(pwd)/frontend:/app/frontend \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

여기서:
- `$(pwd)/backend:/app/backend` → 로컬의 `backend` 폴더를 컨테이너의 `/app/backend`에 마운트
- `$(pwd)/frontend:/app/frontend` → 로컬의 `frontend` 폴더를 컨테이너의 `/app/frontend`에 마운트

이렇게 하면 컨테이너 안에서 돌아가는 Open WebUI가 로컬에서 수정한 코드로 실행돼.

---

### **3. Docker Compose 사용 (더 추천)**
Docker Compose를 사용하면 더 깔끔하게 관리할 수 있어.

#### **(1) `docker-compose.override.yml` 생성**
```yaml
version: '3'
services:
  open-webui:
    volumes:
      - ./backend:/app/backend
      - ./frontend:/app/frontend
```

#### **(2) 컨테이너 실행**
```bash
docker compose up -d
```
이러면 로컬 코드가 자동으로 반영된 상태에서 실행돼.

---

### **4. 컨테이너 내부에서 코드 수정 확인**
컨테이너에 들어가서 코드가 잘 반영됐는지 확인해보자.
```bash
docker exec -it open-webui /bin/sh
```
그리고 `/app/backend` 또는 `/app/frontend`로 이동해서 코드가 마운트된 걸 확인할 수 있어.

---

### **5. 코드 수정 후 반영**
로컬에서 소스를 수정하면 컨테이너 안에서도 자동으로 반영되지만, FastAPI나 프론트엔드 빌드가 필요할 수도 있어.

#### **(1) 백엔드 (FastAPI) 변경 반영**
```bash
docker restart open-webui
```
or
```bash
docker exec -it open-webui pkill -9 -f "uvicorn"
docker exec -it open-webui /bin/sh -c "cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8080"
```

#### **(2) 프론트엔드 변경 반영**
```bash
docker exec -it open-webui /bin/sh -c "cd /app/frontend && npm run build"
docker restart open-webui
```

---

# 서버 재시작 방법

## 1. 개발중일때 서버만 가볍게 재시작
docker exec -it open-webui bash
pkill -f 'uvicorn'
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

## 2. 운영중일때 컨테이너 수준에서 서버만 재시작
docker compose restart open-webui



----------------------------------
# 파이썬 환경 설정
----------------------------------
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

pnpm build

---
cd backend
source venv/bin/activate  # Mac/Linux
python3 main.py

---
### 1. backend 실행
cd backend 
conda activate openwebui
start.sh

### 2. frontend 실행
cd frontend 
pnpm dev



----------------------------------
# 작업이력
----------------------------------

## 2024/02/24

### 신규 화면 추가



## 2024/02/20
### 소스 수정
backend/open_webui/routers
backend/open_webui/routers/alfred.py
backend/open_webui/config.py
backend/open_webui/env.py
backend/open_webui/main.py
src/lib/constants.ts
src/.webui_secret_key
README.alfred.md
docker-compose.yaml # ollama관련 컨테이너 제거 + 로컬디스크와 마운트
run-compose.sh

### 이미지 수정
backend/open_webui/static/logo.png
static/static/favicon.png
static/static/splash-dark.png
static/static/splash.png
