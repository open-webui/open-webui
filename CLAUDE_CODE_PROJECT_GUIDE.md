# Open WebUI 프로젝트 상세 분석 가이드

> Claude Code로 효율적으로 수정하기 위한 프로젝트 구조 및 아키텍처 분석 문서

버전: 0.6.34
작성일: 2025-11-03

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택](#기술-스택)
3. [프로젝트 구조](#프로젝트-구조)
4. [백엔드 아키텍처](#백엔드-아키텍처)
5. [프론트엔드 아키텍처](#프론트엔드-아키텍처)
6. [주요 기능 위치](#주요-기능-위치)
7. [개발 환경 설정](#개발-환경-설정)
8. [수정 시 주의사항](#수정-시-주의사항)

---

## 프로젝트 개요

Open WebUI는 **확장 가능하고 사용자 친화적인 자체 호스팅 AI 플랫폼**입니다.

### 핵심 특징
- 🤖 다중 LLM 제공자 지원 (Ollama, OpenAI, Azure, Google, Anthropic 등)
- 📚 RAG (Retrieval Augmented Generation) 시스템
- 🔌 Python 기반 Functions/Pipelines 확장 시스템
- 🎨 이미지 생성 (DALL-E, ComfyUI, AUTOMATIC1111)
- 🎤 음성 입출력 (STT/TTS)
- 🌐 웹 검색 통합
- 👥 사용자/그룹 관리 및 권한 제어
- 🔐 OAuth, LDAP, SCIM 인증 지원

---

## 기술 스택

### 백엔드
```
언어: Python 3.11-3.12
프레임워크: FastAPI 0.118.0
서버: Uvicorn 0.37.0
ORM: SQLAlchemy 2.0.38, Peewee 3.18.1
데이터베이스: SQLite (기본), PostgreSQL, MySQL, Oracle
캐싱: Redis (선택적)
WebSocket: Python-SocketIO 5.13.0
인증: PyJWT 2.10.1, Authlib 1.6.5, python-jose 3.4.0
```

### 프론트엔드
```
프레임워크: SvelteKit ^2.5.20
언어: TypeScript ^5.5.4
빌드 도구: Vite ^5.4.14
스타일링: TailwindCSS ^4.0.0
리치 텍스트 에디터: Tiptap ^3.0.7
실시간 협업: Yjs ^13.6.27, Prosemirror
차트: Chart.js ^4.5.0
PDF: jsPDF ^3.0.0, pdfjs-dist ^5.4.149
코드 에디터: CodeMirror ^6.0.1
```

### AI/ML 라이브러리
```
LangChain: 0.3.27
Transformers: 최신 버전
Sentence-Transformers: 5.1.1
ChromaDB: 1.0.20 (벡터 DB)
OpenSearch: 2.8.0
Faster-Whisper: 1.1.1 (STT)
```

---

## 프로젝트 구조

### 루트 디렉토리
```
open-webui/
├── backend/                    # Python 백엔드
│   └── open_webui/            # 메인 패키지
│       ├── main.py            # FastAPI 앱 진입점 ⭐
│       ├── config.py          # 설정 관리 ⭐
│       ├── env.py             # 환경 변수
│       ├── constants.py       # 상수 정의
│       ├── models/            # 데이터베이스 모델
│       ├── routers/           # API 라우터
│       ├── utils/             # 유틸리티 함수
│       ├── retrieval/         # RAG 시스템
│       ├── socket/            # WebSocket 처리
│       ├── internal/          # 내부 모듈
│       ├── storage/           # 스토리지 관리
│       └── migrations/        # DB 마이그레이션
├── src/                       # Svelte 프론트엔드
│   ├── lib/                   # 라이브러리 코드
│   │   ├── apis/              # API 클라이언트
│   │   ├── components/        # Svelte 컴포넌트
│   │   ├── stores/            # 전역 상태 관리
│   │   ├── utils/             # 유틸리티 함수
│   │   └── i18n/              # 다국어 지원
│   └── routes/                # 페이지 라우트
│       ├── (app)/             # 메인 앱
│       ├── auth/              # 인증 페이지
│       └── error/             # 에러 페이지
├── static/                    # 정적 파일
├── Dockerfile                 # Docker 이미지 빌드
├── docker-compose.yaml        # Docker Compose 설정
├── package.json               # Node.js 의존성
├── pyproject.toml            # Python 의존성
└── vite.config.ts            # Vite 설정
```

---

## 백엔드 아키텍처

### 1. 메인 애플리케이션 (main.py)

**위치**: `backend/open_webui/main.py`

**핵심 구성요소**:
```python
# 라인 611: FastAPI 앱 초기화
app = FastAPI(
    title="Open WebUI",
    docs_url="/docs" if ENV == "dev" else None,
    lifespan=lifespan,
)

# 라인 548-609: 라이프사이클 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 초기화
    - Redis 연결
    - 외부 의존성 설치
    - 모델 캐싱
    yield
    # 앱 종료 시 정리
```

**주요 엔드포인트**:
- `/api/chat/completions` (라인 1431): 채팅 완료
- `/api/models` (라인 1345): 모델 목록
- `/api/embeddings` (라인 1404): 임베딩 생성
- `/api/config` (라인 1696): 앱 설정

### 2. API 라우터

**위치**: `backend/open_webui/routers/`

```
routers/
├── auths.py          # 인증 (로그인, 회원가입, JWT)
├── users.py          # 사용자 관리
├── groups.py         # 그룹 관리
├── chats.py          # 채팅 이력
├── channels.py       # 채널 (협업)
├── notes.py          # 노트
├── folders.py        # 폴더 구조
├── models.py         # 모델 관리
├── knowledge.py      # 지식 베이스
├── files.py          # 파일 업로드/관리
├── functions.py      # Python 함수
├── tools.py          # 도구
├── prompts.py        # 프롬프트 템플릿
├── memories.py       # 메모리
├── ollama.py         # Ollama API 프록시
├── openai.py         # OpenAI API 프록시
├── pipelines.py      # 파이프라인
├── tasks.py          # 백그라운드 작업
├── images.py         # 이미지 생성
├── audio.py          # 음성 (STT/TTS)
├── retrieval.py      # RAG 검색
├── configs.py        # 설정 관리
├── evaluations.py    # 모델 평가
├── scim.py           # SCIM 2.0
└── utils.py          # 유틸리티 엔드포인트
```

**라우터 등록** (main.py 라인 1283-1323):
```python
app.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
app.include_router(openai.router, prefix="/openai", tags=["openai"])
app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
# ... 등등
```

### 3. 데이터베이스 모델

**위치**: `backend/open_webui/models/`

**주요 모델**:
```python
models/
├── users.py          # User, Auth, ApiKey
├── chats.py          # Chat, Message
├── channels.py       # Channel, ChannelMessage
├── notes.py          # Note
├── folders.py        # Folder
├── models.py         # Model (메타데이터)
├── knowledge.py      # Knowledge, KnowledgeFile
├── files.py          # File
├── functions.py      # Function
├── tools.py          # Tool
├── prompts.py        # Prompt
├── memories.py       # Memory
├── groups.py         # Group, GroupUser
├── configs.py        # Config
└── feedbacks.py      # Feedback
```

**예시** - User 모델:
```python
class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    role = Column(String)  # admin, user, pending
    profile_image_url = Column(Text)
    created_at = Column(Integer)
    updated_at = Column(Integer)
```

### 4. RAG 시스템

**위치**: `backend/open_webui/retrieval/`

```
retrieval/
├── main.py           # RAG 메인 로직
├── loaders/          # 문서 로더
│   ├── youtube.py    # YouTube 트랜스크립트
│   ├── web.py        # 웹 스크래핑
│   └── main.py       # 통합 로더
├── web/              # 웹 검색
│   ├── main.py       # 검색 통합
│   ├── brave.py      # Brave Search
│   ├── google.py     # Google PSE
│   ├── searxng.py    # SearXNG
│   ├── tavily.py     # Tavily
│   └── ...           # 기타 검색 엔진
└── vector/           # 벡터 DB
    ├── dbs/
    │   ├── chroma.py     # ChromaDB
    │   ├── opensearch.py # OpenSearch
    │   ├── milvus.py     # Milvus
    │   └── qdrant.py     # Qdrant
    └── connector.py      # DB 커넥터
```

**RAG 워크플로우**:
1. 문서 업로드 → 청킹 (CHUNK_SIZE, CHUNK_OVERLAP)
2. 임베딩 생성 → 벡터 DB 저장
3. 쿼리 → 벡터 검색 + 리랭킹
4. 컨텍스트 삽입 → LLM 생성

### 5. 설정 시스템

**위치**: `backend/open_webui/config.py` (110KB, 420줄)

**설정 카테고리**:
```python
# Ollama 설정
ENABLE_OLLAMA_API = bool
OLLAMA_BASE_URLS = list[str]

# OpenAI 설정
ENABLE_OPENAI_API = bool
OPENAI_API_BASE_URLS = list[str]
OPENAI_API_KEYS = list[str]

# RAG 설정
RAG_EMBEDDING_MODEL = str
RAG_TOP_K = int
RAG_RELEVANCE_THRESHOLD = float
CHUNK_SIZE = int
CHUNK_OVERLAP = int

# 이미지 생성
IMAGE_GENERATION_ENGINE = str  # openai, comfyui, automatic1111
IMAGE_GENERATION_MODEL = str

# 음성
AUDIO_STT_ENGINE = str  # openai, whisper, deepgram, azure
AUDIO_TTS_ENGINE = str  # openai, elevenlabs, azure

# 인증
ENABLE_OAUTH_ROLE_MANAGEMENT = bool
ENABLE_LDAP = bool
SCIM_ENABLED = bool

# WebUI
ENABLE_SIGNUP = bool
DEFAULT_USER_ROLE = str
USER_PERMISSIONS = dict
```

**설정 동적 업데이트**:
```python
# 라인 628: AppConfig 클래스
app.state.config = AppConfig(
    redis_url=REDIS_URL,
    redis_sentinels=...,
)
```

### 6. WebSocket (실시간 통신)

**위치**: `backend/open_webui/socket/main.py`

**기능**:
- 실시간 채팅 스트리밍
- 협업 편집 (Yjs)
- 사용자 상태 추적
- 이벤트 브로드캐스팅

```python
@sio.on("connect")
async def connect(sid, environ, auth):
    # 연결 처리

@sio.on("chat:stream")
async def stream_chat(sid, data):
    # 채팅 스트리밍
```

### 7. 태스크 시스템

**위치**: `backend/open_webui/tasks.py`

**기능**:
- 비동기 태스크 실행 (Redis 기반)
- 백그라운드 작업 (제목 생성, 태그 생성)
- 태스크 취소/모니터링

---

## 프론트엔드 아키텍처

### 1. SvelteKit 라우팅

**위치**: `src/routes/`

```
routes/
├── +layout.svelte       # 루트 레이아웃 (19KB)
├── +layout.js           # 레이아웃 로직
├── (app)/               # 메인 앱 (인증 필요)
│   ├── +layout.svelte   # 앱 레이아웃
│   ├── +page.svelte     # 홈/채팅
│   ├── c/               # 채팅
│   │   └── [id]/
│   ├── w/               # 워크스페이스
│   ├── channels/        # 채널
│   ├── notes/           # 노트
│   ├── knowledge/       # 지식 베이스
│   ├── models/          # 모델 관리
│   ├── prompts/         # 프롬프트
│   ├── tools/           # 도구
│   └── admin/           # 관리자
│       ├── settings/    # 설정
│       └── users/       # 사용자 관리
├── auth/                # 인증 페이지
│   ├── signin/
│   └── signup/
└── error/               # 에러 페이지
```

### 2. 컴포넌트 구조

**위치**: `src/lib/components/`

```
components/
├── chat/                # 채팅 UI
│   ├── Chat.svelte              # 채팅 컨테이너
│   ├── Messages.svelte          # 메시지 리스트
│   ├── MessageInput.svelte      # 입력창
│   ├── ModelSelector.svelte     # 모델 선택
│   └── Settings.svelte          # 채팅 설정
├── workspace/           # 워크스페이스
├── channels/            # 채널
├── notes/               # 노트
├── knowledge/           # 지식 베이스
├── models/              # 모델
├── prompts/             # 프롬프트
├── tools/               # 도구
├── functions/           # 함수
├── admin/               # 관리자
├── common/              # 공통 컴포넌트
│   ├── Modal.svelte
│   ├── Button.svelte
│   ├── Input.svelte
│   └── Tooltip.svelte
├── icons/               # 아이콘
└── layout/              # 레이아웃
    ├── Navbar.svelte
    ├── Sidebar.svelte
    └── Footer.svelte
```

### 3. 상태 관리 (Svelte Stores)

**위치**: `src/lib/stores/`

```javascript
// stores/
├── index.ts             # 스토어 엔트리포인트
├── user.ts              # 사용자 상태
├── config.ts            # 앱 설정
├── models.ts            # 모델 리스트
├── chats.ts             # 채팅 이력
├── knowledge.ts         # 지식 베이스
├── prompts.ts           # 프롬프트
└── settings.ts          # 사용자 설정
```

**예시**:
```typescript
// user.ts
import { writable } from 'svelte/store';

export const user = writable<User | null>(null);
export const isAuthenticated = derived(user, $user => !!$user);

// config.ts
export const config = writable<Config>({
    version: '',
    default_models: [],
    features: {}
});
```

### 4. API 클라이언트

**위치**: `src/lib/apis/`

```
apis/
├── index.ts             # API 기본 설정
├── auths/               # 인증 API
├── users/               # 사용자 API
├── chats/               # 채팅 API
├── channels/            # 채널 API
├── notes/               # 노트 API
├── knowledge/           # 지식 베이스 API
├── models/              # 모델 API
├── prompts/             # 프롬프트 API
├── tools/               # 도구 API
├── functions/           # 함수 API
├── files/               # 파일 API
├── images/              # 이미지 API
├── audio/               # 음성 API
├── ollama/              # Ollama API
├── openai/              # OpenAI API
└── utils/               # 유틸리티 API
```

**예시**:
```typescript
// chats/index.ts
export const createNewChat = async (token: string, chat: object) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/new`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(chat)
    });
    return res.json();
};

export const getChatById = async (token: string, id: string) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return res.json();
};
```

### 5. 유틸리티 함수

**위치**: `src/lib/utils/`

```
utils/
├── index.ts             # 일반 유틸
├── markdown.ts          # 마크다운 렌더링
├── chat.ts              # 채팅 로직
├── files.ts             # 파일 처리
├── audio.ts             # 음성 처리
└── i18n.ts              # 국제화
```

---

## 주요 기능 위치

### 1. 채팅 시스템

**백엔드**:
- 엔드포인트: `backend/open_webui/main.py:1431` (`/api/chat/completions`)
- 핸들러: `backend/open_webui/utils/chat.py:generate_chat_completion`
- 모델: `backend/open_webui/models/chats.py`

**프론트엔드**:
- 페이지: `src/routes/(app)/+page.svelte`
- 컴포넌트: `src/lib/components/chat/Chat.svelte`
- API: `src/lib/apis/chats/index.ts`
- 스토어: `src/lib/stores/chats.ts`

### 2. 모델 관리

**백엔드**:
- 라우터: `backend/open_webui/routers/models.py`
- 모델: `backend/open_webui/models/models.py`
- 유틸: `backend/open_webui/utils/models.py`

**프론트엔드**:
- 페이지: `src/routes/(app)/admin/settings/models/+page.svelte`
- API: `src/lib/apis/models/index.ts`

### 3. RAG (지식 베이스)

**백엔드**:
- 라우터: `backend/open_webui/routers/retrieval.py`
- 지식베이스: `backend/open_webui/routers/knowledge.py`
- 파일 처리: `backend/open_webui/routers/files.py`
- RAG 로직: `backend/open_webui/retrieval/main.py`

**프론트엔드**:
- 페이지: `src/routes/(app)/knowledge/+page.svelte`
- 컴포넌트: `src/lib/components/knowledge/`
- API: `src/lib/apis/knowledge/index.ts`

### 4. Functions/Tools (확장 시스템)

**백엔드**:
- Functions: `backend/open_webui/routers/functions.py`
- Tools: `backend/open_webui/routers/tools.py`
- 모델: `backend/open_webui/models/functions.py`, `models/tools.py`

**프론트엔드**:
- Functions 페이지: `src/routes/(app)/workspace/functions/+page.svelte`
- Tools 페이지: `src/routes/(app)/workspace/tools/+page.svelte`

### 5. 사용자 인증

**백엔드**:
- 라우터: `backend/open_webui/routers/auths.py`
- 모델: `backend/open_webui/models/users.py`
- 유틸: `backend/open_webui/utils/auth.py`
- OAuth: `backend/open_webui/utils/oauth.py`
- LDAP: LDAP 관련 설정은 `config.py`에서

**프론트엔드**:
- 로그인: `src/routes/auth/signin/+page.svelte`
- 회원가입: `src/routes/auth/signup/+page.svelte`
- API: `src/lib/apis/auths/index.ts`

### 6. 이미지 생성

**백엔드**:
- 라우터: `backend/open_webui/routers/images.py`
- 설정: `config.py` (IMAGE_GENERATION_ENGINE, IMAGE_GENERATION_MODEL)

**프론트엔드**:
- 설정: `src/routes/(app)/admin/settings/images/+page.svelte`
- API: `src/lib/apis/images/index.ts`

### 7. 음성 (STT/TTS)

**백엔드**:
- 라우터: `backend/open_webui/routers/audio.py`
- 설정: `config.py` (AUDIO_STT_ENGINE, AUDIO_TTS_ENGINE)

**프론트엔드**:
- 설정: `src/routes/(app)/admin/settings/audio/+page.svelte`
- API: `src/lib/apis/audio/index.ts`

### 8. 관리자 패널

**프론트엔드**:
```
src/routes/(app)/admin/
├── settings/
│   ├── +page.svelte         # 일반 설정
│   ├── connections/         # 연결 설정
│   ├── database/            # 데이터베이스
│   ├── models/              # 모델
│   ├── documents/           # 문서/RAG
│   ├── images/              # 이미지
│   ├── audio/               # 음성
│   ├── interface/           # 인터페이스
│   └── users/               # 사용자 관리
└── knowledge/               # 지식 베이스 관리
```

---

## 개발 환경 설정

### 1. 필수 요구사항

```bash
# 시스템 요구사항
Python: 3.11 - 3.12
Node.js: 18.13.0 - 22.x.x
npm: >= 6.0.0
```

### 2. 로컬 개발 설정

**백엔드 설정**:
```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
cd backend
pip install -e .

# 개발 서버 실행
cd open_webui
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

**프론트엔드 설정**:
```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
# 또는 포트 지정
npm run dev:5050

# 빌드
npm run build

# 타입 체크
npm run check
```

### 3. Docker 개발 환경

```bash
# Docker Compose로 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f open-webui

# 재빌드
docker-compose up -d --build
```

### 4. 환경 변수

**주요 환경 변수** (`.env` 파일 또는 Docker 환경):

```bash
# 데이터베이스
DATA_DIR=/app/backend/data
DATABASE_URL=sqlite:///webui.db

# Ollama
ENABLE_OLLAMA_API=True
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI
ENABLE_OPENAI_API=True
OPENAI_API_BASE_URLS=https://api.openai.com/v1
OPENAI_API_KEYS=sk-...

# 인증
WEBUI_SECRET_KEY=랜덤_시크릿_키
ENABLE_SIGNUP=True
DEFAULT_USER_ROLE=user

# Redis (선택적)
REDIS_URL=redis://localhost:6379/0

# RAG
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1500
CHUNK_OVERLAP=100

# 이미지 생성
ENABLE_IMAGE_GENERATION=True
IMAGE_GENERATION_ENGINE=openai
AUTOMATIC1111_BASE_URL=http://localhost:7860

# 음성
AUDIO_STT_ENGINE=openai
AUDIO_TTS_ENGINE=openai
```

---

## 수정 시 주의사항

### 1. 백엔드 수정 가이드

#### API 라우터 추가
```python
# backend/open_webui/routers/my_feature.py
from fastapi import APIRouter, Depends
from open_webui.utils.auth import get_verified_user

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(user=Depends(get_verified_user)):
    return {"status": "success"}

# main.py에 등록
app.include_router(
    my_feature.router,
    prefix="/api/v1/my-feature",
    tags=["my-feature"]
)
```

#### 데이터베이스 모델 추가
```python
# backend/open_webui/models/my_model.py
from sqlalchemy import Column, String, Integer, Text
from open_webui.internal.db import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(Integer)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at
        }

# 마이그레이션 생성
alembic revision --autogenerate -m "Add my_table"
alembic upgrade head
```

#### 설정 추가
```python
# backend/open_webui/env.py
MY_FEATURE_ENABLED = os.getenv("MY_FEATURE_ENABLED", "False").lower() == "true"

# backend/open_webui/config.py
from open_webui.env import MY_FEATURE_ENABLED

# main.py에서 사용
app.state.config.MY_FEATURE_ENABLED = MY_FEATURE_ENABLED
```

### 2. 프론트엔드 수정 가이드

#### 새 페이지 추가
```svelte
<!-- src/routes/(app)/my-feature/+page.svelte -->
<script lang="ts">
    import { onMount } from 'svelte';
    import { user } from '$lib/stores';

    let data = [];

    onMount(async () => {
        // 데이터 로드
    });
</script>

<div class="container">
    <h1>My Feature</h1>
    <!-- 컨텐츠 -->
</div>
```

#### API 클라이언트 추가
```typescript
// src/lib/apis/my-feature/index.ts
import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getMyData = async (token: string) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/my-feature/data`, {
        method: 'GET',
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    if (!res.ok) throw new Error('Failed to fetch data');
    return res.json();
};
```

#### 스토어 추가
```typescript
// src/lib/stores/my-feature.ts
import { writable } from 'svelte/store';

export interface MyFeatureData {
    id: string;
    name: string;
}

export const myFeatureData = writable<MyFeatureData[]>([]);
```

#### 컴포넌트 추가
```svelte
<!-- src/lib/components/my-feature/MyComponent.svelte -->
<script lang="ts">
    export let title: string;
    export let onAction: () => void;
</script>

<div class="my-component">
    <h2>{title}</h2>
    <button on:click={onAction}>Action</button>
</div>

<style>
    .my-component {
        /* Tailwind 사용 권장 */
    }
</style>
```

### 3. 통합 기능 추가 (풀스택)

**예시: 새로운 "Bookmarks" 기능 추가**

1. **데이터베이스 모델**:
```python
# backend/open_webui/models/bookmarks.py
class Bookmark(Base):
    __tablename__ = "bookmark"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    title = Column(String)
    url = Column(Text)
    created_at = Column(Integer)
```

2. **API 라우터**:
```python
# backend/open_webui/routers/bookmarks.py
@router.get("/")
async def get_bookmarks(user=Depends(get_verified_user)):
    return Bookmarks.get_bookmarks_by_user_id(user.id)

@router.post("/new")
async def create_bookmark(form_data: BookmarkForm, user=Depends(get_verified_user)):
    bookmark = Bookmarks.insert_new_bookmark(user.id, form_data)
    return bookmark
```

3. **프론트엔드 API**:
```typescript
// src/lib/apis/bookmarks/index.ts
export const getBookmarks = async (token: string) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/bookmarks`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return res.json();
};
```

4. **프론트엔드 페이지**:
```svelte
<!-- src/routes/(app)/bookmarks/+page.svelte -->
<script lang="ts">
    import { getBookmarks } from '$lib/apis/bookmarks';
    import { user } from '$lib/stores';

    let bookmarks = [];

    onMount(async () => {
        bookmarks = await getBookmarks($user.token);
    });
</script>

<div>
    {#each bookmarks as bookmark}
        <div>{bookmark.title}</div>
    {/each}
</div>
```

### 4. 코드 스타일 가이드

**Python (백엔드)**:
```python
# Black 포매터 사용
black backend/

# Pylint 린팅
pylint backend/

# 타입 힌트 사용
def get_user_by_id(user_id: str) -> Optional[User]:
    return Users.get_user_by_id(user_id)
```

**TypeScript/Svelte (프론트엔드)**:
```bash
# Prettier 포매터
npm run format

# ESLint 린팅
npm run lint

# 타입 체크
npm run check
```

### 5. 테스트

**백엔드 테스트**:
```python
# backend/open_webui/test/test_my_feature.py
import pytest
from open_webui.models.users import Users

def test_get_user():
    user = Users.get_user_by_id("test_id")
    assert user is not None
```

**프론트엔드 테스트**:
```bash
# Vitest 실행
npm run test:frontend
```

### 6. 주의사항

#### 보안
- **항상 `get_verified_user` 의존성 사용**: 인증이 필요한 엔드포인트에는 반드시 추가
- **SQL 인젝션 방지**: SQLAlchemy ORM 사용, raw SQL 쿼리 최소화
- **XSS 방지**: DOMPurify로 HTML 새니타이징
- **CSRF 방지**: 토큰 기반 인증 사용

#### 성능
- **데이터베이스 인덱스**: 자주 쿼리하는 필드에 인덱스 추가
- **캐싱**: Redis 활용 (특히 모델 리스트, 임베딩 함수)
- **비동기 처리**: `async/await` 사용
- **페이지네이션**: 대량 데이터는 페이지네이션 구현

#### 호환성
- **버전 호환성**: Python 3.11-3.12, Node 18-22 지원
- **브라우저 호환성**: 모던 브라우저 (Chrome, Firefox, Safari, Edge)
- **모바일 대응**: 반응형 디자인 (Tailwind 유틸리티 사용)

#### 마이그레이션
- **데이터베이스 변경 시 마이그레이션 필수**:
```bash
cd backend
alembic revision --autogenerate -m "설명"
alembic upgrade head
```

#### 국제화 (i18n)
- 텍스트는 항상 번역 키로 관리:
```typescript
// src/lib/i18n/locales/en.json
{
    "my_feature": {
        "title": "My Feature",
        "description": "This is my feature"
    }
}

// Svelte 컴포넌트에서
import { i18n } from '$lib/i18n';
$i18n.t('my_feature.title')
```

---

## 주요 파일 참조

### 빠른 참조 (수정 빈도 높음)

| 파일 | 위치 | 용도 |
|------|------|------|
| FastAPI 앱 | `backend/open_webui/main.py` | 백엔드 진입점, 라우터 등록 |
| 설정 | `backend/open_webui/config.py` | 모든 설정 변수 |
| 환경 변수 | `backend/open_webui/env.py` | 환경 변수 로드 |
| 데이터베이스 | `backend/open_webui/internal/db.py` | DB 연결, 세션 |
| 채팅 핸들러 | `backend/open_webui/utils/chat.py` | 채팅 로직 |
| 모델 유틸 | `backend/open_webui/utils/models.py` | 모델 필터링, 접근 제어 |
| 인증 유틸 | `backend/open_webui/utils/auth.py` | JWT, 사용자 검증 |
| 루트 레이아웃 | `src/routes/+layout.svelte` | 전역 레이아웃 |
| 채팅 페이지 | `src/routes/(app)/+page.svelte` | 메인 채팅 UI |
| 사용자 스토어 | `src/lib/stores/user.ts` | 사용자 상태 |
| 설정 스토어 | `src/lib/stores/config.ts` | 앱 설정 |
| API 클라이언트 | `src/lib/apis/` | 모든 API 호출 |

### 설정 파일

| 파일 | 용도 |
|------|------|
| `pyproject.toml` | Python 의존성 |
| `package.json` | Node.js 의존성 |
| `docker-compose.yaml` | Docker 개발 환경 |
| `Dockerfile` | Docker 이미지 빌드 |
| `vite.config.ts` | Vite 빌드 설정 |
| `svelte.config.js` | SvelteKit 설정 |
| `tailwind.config.ts` | Tailwind CSS 설정 |
| `tsconfig.json` | TypeScript 설정 |

---

## 일반적인 수정 시나리오

### 시나리오 1: 새 LLM 제공자 추가

1. **설정 추가** (`backend/open_webui/env.py`, `config.py`):
```python
MY_LLM_API_KEY = os.getenv("MY_LLM_API_KEY")
MY_LLM_BASE_URL = os.getenv("MY_LLM_BASE_URL", "https://api.myllm.com")
```

2. **프록시 라우터 생성** (`backend/open_webui/routers/my_llm.py`):
```python
@router.post("/chat/completions")
async def chat_completions(form_data: dict):
    # MY_LLM API 호출
    pass
```

3. **모델 리스트 통합** (`backend/open_webui/utils/models.py`):
```python
async def get_my_llm_models():
    # MY_LLM 모델 가져오기
    pass
```

4. **프론트엔드 설정 UI** (`src/routes/(app)/admin/settings/connections/+page.svelte`):
```svelte
<!-- MY_LLM API Key 입력 폼 -->
```

### 시나리오 2: 새 파일 타입 지원 (RAG)

1. **파일 로더 추가** (`backend/open_webui/retrieval/loaders/my_loader.py`):
```python
def load_my_file(file_path: str) -> str:
    # 파일 파싱 로직
    return text_content
```

2. **메인 로더에 통합** (`backend/open_webui/retrieval/main.py`):
```python
if file_ext == ".myext":
    content = load_my_file(file_path)
```

3. **설정 업데이트** (`config.py`):
```python
RAG_ALLOWED_FILE_EXTENSIONS = [".pdf", ".txt", ".myext"]
```

### 시나리오 3: 새 관리자 설정 페이지 추가

1. **백엔드 설정 추가** (`config.py`, `env.py`)
2. **API 엔드포인트** (`backend/open_webui/routers/configs.py`)
3. **프론트엔드 페이지** (`src/routes/(app)/admin/settings/my-setting/+page.svelte`)
4. **네비게이션 추가** (관리자 사이드바)

---

## 디버깅 팁

### 백엔드 디버깅

**로그 레벨 설정**:
```python
# backend/open_webui/env.py
GLOBAL_LOG_LEVEL = "DEBUG"
SRC_LOG_LEVELS = {
    "MAIN": "DEBUG",
    "MODELS": "DEBUG",
}
```

**FastAPI 개발자 문서**:
```
http://localhost:8080/docs
```

**데이터베이스 직접 쿼리**:
```python
from open_webui.internal.db import Session
from sqlalchemy import text

Session.execute(text("SELECT * FROM user")).all()
```

### 프론트엔드 디버깅

**Svelte DevTools**: 브라우저 확장 설치

**Console 로깅**:
```typescript
console.log('Data:', data);
```

**네트워크 탭**: API 요청/응답 확인

**Hot Module Replacement (HMR)**: Vite 자동 리로드

---

## 추가 리소스

- **공식 문서**: https://docs.openwebui.com/
- **GitHub**: https://github.com/open-webui/open-webui
- **Discord**: https://discord.gg/5rJgQTnV4s
- **기여 가이드**: https://github.com/open-webui/open-webui/blob/main/CONTRIBUTING.md

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-11-03
**프로젝트 버전**: 0.6.34

이 문서를 통해 Open WebUI 프로젝트의 구조를 명확히 이해하고, Claude Code를 사용한 효율적인 수정 작업을 수행할 수 있습니다.
