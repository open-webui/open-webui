## 📘 MergeFeat OpenWebUI Client

`mergefeat_openwebui.py`는 로컬에서 실행 중인 OpenWebUI 또는 호환되는 Chat Completion API 서버에 요청을 보내는 Python 클라이언트입니다.  
다른 프로젝트에서 다음처럼 임포트해서 사용할 수 있습니다:

```python
import mergefeat_openwebui as mfowui
```

---

## 📦 설치 및 준비

### 1. `mergefeat_openwebui.py`를 프로젝트 폴더에 넣기

예시 구조:

```
your_project/
├── main.py
└── mergefeat_openwebui.py
```

### 2. 의존성 설치

```bash
pip install requests
```

---

## 🛠️ 사용법

### 1. 모듈 임포트

```python
import mergefeat_openwebui as mfowui
```

### 2. API 키 및 서버 주소 설정 (필요 시)

```python
mfowui.api_key = 'your_api_key_here'
mfowui.host = 'http://localhost:8080'
mfowui.chat_completion_api_endpoint = '/api/chat/completions'
```

### 3. Chat Completion 요청

```python
messages = [
    {
        'role': 'user',
        'content': 'Explain quantum computing in simple terms.'
    }
]

response = mfowui.ChatCompletion.create(
    model='your-model-name',
    messages=messages,
    max_completion_tokens=512,
    temperature=0.5,
    num_ctx=2048
)

print(response.json())
```

---

## 🎛️ 주요 파라미터

|이름|설명|
|---|---|
|`model`|사용할 언어 모델 이름|
|`messages`|채팅 메시지 리스트 (`role`, `content`)|
|`max_completion_tokens`|최대 응답 토큰 수|
|`temperature`|창의성 조절 (0~1)|
|`num_ctx`|최대 context 크기|
