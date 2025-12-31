"""
Gemini File Search RAG API 라우터

챕터별 PDF 파일을 관리하고 RAG 쿼리를 수행하는 엔드포인트를 제공합니다.
"""

import logging
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.gemini_rag import get_gemini_rag_service, GeminiRAGService
from open_webui.utils.prompt_composer import compose_with_fallback
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.textbooks import TextbookChapters
from open_webui.models.chats import Chats, ChatForm

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


# ============================================================
# Pydantic 모델
# ============================================================

class StoreCreateRequest(BaseModel):
    display_name: str


class StoreResponse(BaseModel):
    name: str
    display_name: str
    success: bool = True
    error: Optional[str] = None


class StoreListResponse(BaseModel):
    stores: List[dict]


class FileUploadResponse(BaseModel):
    success: bool
    operation_name: Optional[str] = None
    done: Optional[bool] = None
    error: Optional[str] = None


class RAGQueryRequest(BaseModel):
    question: str
    store_names: List[str]
    model: str = "gemini-2.5-flash"
    temperature: float = 0.2
    system_instruction: Optional[str] = None
    prompt_group_id: Optional[str] = None
    proficiency_level: Optional[str] = None
    response_style: Optional[str] = None


class RAGQueryResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    citations: List[dict] = []
    model: Optional[str] = None
    error: Optional[str] = None
    chat_id: Optional[str] = None  # Returned if a new chat was created


class ChapterStoreMapping(BaseModel):
    chapter_id: str
    store_name: str
    display_name: str


# ============================================================
# 챕터-Store 매핑 관리 (DB 연동)
# ============================================================
# 매핑은 TextbookChapter.rag_store_name 필드에 저장됨


def get_gemini_api_key(request: Request) -> Optional[str]:
    """
    OpenAI 설정에서 Gemini API 키를 찾아서 반환
    generativelanguage.googleapis.com URL에 해당하는 키를 찾음
    """
    try:
        base_urls = request.app.state.config.OPENAI_API_BASE_URLS
        api_keys = request.app.state.config.OPENAI_API_KEYS

        for idx, url in enumerate(base_urls):
            if "generativelanguage.googleapis.com" in url:
                if idx < len(api_keys) and api_keys[idx]:
                    return api_keys[idx]
        return None
    except Exception:
        return None


def get_rag_service(request: Request) -> GeminiRAGService:
    """RAG 서비스 인스턴스 반환"""
    api_key = get_gemini_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key not found. Please configure Gemini in OpenAI settings."
        )
    return get_gemini_rag_service(api_key)


def generate_chat_title_background(
    api_key: str,
    chat_id: str,
    messages: List[dict],
    user_id: str
):
    """
    백그라운드에서 채팅 제목 자동 생성

    Args:
        api_key: Gemini API 키
        chat_id: 채팅 ID
        messages: 대화 내역
        user_id: 사용자 ID
    """
    try:
        log.info(f"[TITLE GEN] Starting title generation for chat {chat_id}")

        # 첫 메시지만 있으면 제목 생성 (이미 제목이 있으면 스킵)
        chat = Chats.get_chat_by_id_and_user_id(chat_id, user_id)
        if not chat:
            log.warning(f"[TITLE GEN] Chat {chat_id} not found for title generation")
            return

        # "새 채팅"이 아니면 이미 제목이 있는 것으로 간주
        if chat.title and chat.title != "새 채팅" and chat.title != "New Chat":
            log.debug(f"[TITLE GEN] Chat {chat_id} already has title: {chat.title}")
            return

        # 메시지 포맷팅
        conversation = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in messages[:3]  # 처음 3개 메시지만 사용
        ])

        # 제목 생성 프롬프트
        title_prompt = f"""다음 대화의 제목을 한국어로 짧게 생성해주세요.
제목은 10단어 이내로, 대화의 핵심 주제를 담아야 합니다.
특수문자나 따옴표 없이 제목만 반환하세요.

대화:
{conversation}

제목:"""

        # Gemini API 직접 호출 (RAG 없이)
        from google import genai
        client = genai.Client(api_key=api_key)

        log.info(f"[TITLE GEN] Calling Gemini API for title generation...")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=title_prompt
        )

        if response and response.text:
            title = response.text.strip()
            # 제목 정리 (따옴표, 특수문자 제거)
            title = title.replace('"', '').replace("'", '').strip()
            # 너무 길면 자르기
            if len(title) > 50:
                title = title[:47] + "..."

            # 채팅 제목 업데이트
            Chats.update_chat_title_by_id(chat_id, title)
            log.info(f"[TITLE GEN] ✅ Generated title for chat {chat_id}: {title}")
        else:
            log.warning(f"[TITLE GEN] No response text for chat {chat_id}")

    except Exception as e:
        log.error(f"[TITLE GEN] Error generating title for chat {chat_id}: {e}")
        import traceback
        log.error(f"[TITLE GEN] Traceback: {traceback.format_exc()}")


# ============================================================
# Store 관리 엔드포인트
# ============================================================

@router.post("/stores", response_model=StoreResponse)
async def create_store(
    request: Request,
    body: StoreCreateRequest,
    user=Depends(get_admin_user)
):
    """
    새로운 File Search Store(코퍼스) 생성 (관리자 전용)

    - **display_name**: Store 표시 이름 (예: "Chapter 1 - ODEs")
    """
    service = get_rag_service(request)
    result = service.create_store(body.display_name)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to create store"))

    return StoreResponse(
        name=result["name"],
        display_name=body.display_name,
        success=True
    )


@router.get("/stores", response_model=StoreListResponse)
async def list_stores(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    모든 Store 목록 조회 (관리자 전용)
    """
    service = get_rag_service(request)
    stores = service.list_stores()
    return StoreListResponse(stores=stores)


@router.get("/stores/{store_name}")
async def get_store(
    store_name: str,
    request: Request,
    user=Depends(get_admin_user)
):
    """
    특정 Store 정보 조회 (관리자 전용)
    """
    service = get_rag_service(request)
    store = service.get_store("fileSearchStores/"+store_name)

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return store


@router.delete("/stores/{store_name}")
async def delete_store(
    store_name: str,
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Store 삭제 (관리자 전용)

    - **store_name**: Store ID (fileSearchStores/ prefix 없이)
    """
    service = get_rag_service(request)
    full_store_name = f"fileSearchStores/{store_name}"
    success = service.delete_store(full_store_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete store")

    # DB에서 해당 Store를 사용하는 챕터들의 매핑 제거
    cleared_chapters = TextbookChapters.clear_rag_store_by_name(full_store_name)

    return {
        "success": True,
        "message": f"Deleted store: {full_store_name}",
        "cleared_chapter_mappings": cleared_chapters
    }


# ============================================================
# 파일 업로드 엔드포인트
# ============================================================

@router.post("/stores/{store_name}/upload", response_model=FileUploadResponse)
async def upload_file_to_store(
    store_name: str,
    request: Request,
    file: UploadFile = File(...),
    max_tokens_per_chunk: int = Form(default=400),
    max_overlap_tokens: int = Form(default=40),
    user=Depends(get_admin_user)
):
    """
    파일을 Store에 업로드 (관리자 전용)

    - **store_name**: 대상 Store ID (fileSearchStores/ prefix 없이)
    - **file**: 업로드할 파일 (PDF 등)
    - **max_tokens_per_chunk**: 청크당 최대 토큰 수 (기본: 400)
    - **max_overlap_tokens**: 청크 간 오버랩 토큰 수 (기본: 40)
    """
    service = get_rag_service(request)

    # store_name에 prefix 추가
    full_store_name = f"fileSearchStores/{store_name}"

    # 파일 읽기
    file_content = await file.read()
    file_name = file.filename or "uploaded_file.pdf"

    result = service.upload_file_bytes(
        file_content=file_content,
        file_name=file_name,
        store_name=full_store_name,
        max_tokens_per_chunk=max_tokens_per_chunk,
        max_overlap_tokens=max_overlap_tokens,
        wait_for_completion=True
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to upload file"))

    return FileUploadResponse(**result)


class FileListResponse(BaseModel):
    files: List[dict]
    store_name: str


@router.get("/stores/{store_name}/files", response_model=FileListResponse)
async def list_files_in_store(
    store_name: str,
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Store 내 파일 목록 조회 (관리자 전용)

    - **store_name**: Store ID (fileSearchStores/ prefix 없이)
    """
    api_key = get_gemini_api_key(request)
    service = get_rag_service(request)
    full_store_name = f"fileSearchStores/{store_name}"
    files = service.list_files(full_store_name, api_key=api_key)
    return FileListResponse(files=files, store_name=full_store_name)


# ============================================================
# 챕터-Store 매핑 엔드포인트 (DB 연동)
# ============================================================

@router.post("/chapter-mapping")
async def set_chapter_store_mapping(
    mapping: ChapterStoreMapping,
    user=Depends(get_admin_user)
):
    """
    챕터 ID와 Store 매핑 설정 (관리자 전용)

    - **chapter_id**: 챕터 ID (예: "ch-1")
    - **store_name**: Store 이름 (예: "fileSearchStores/xxx")
    - **display_name**: 표시 이름 (무시됨, 챕터 제목 사용)
    """
    chapter = TextbookChapters.set_rag_store(mapping.chapter_id, mapping.store_name)
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {mapping.chapter_id}")

    return {
        "success": True,
        "mapping": {
            "chapter_id": chapter.id,
            "store_name": chapter.rag_store_name,
            "display_name": chapter.title
        }
    }


@router.get("/chapter-mapping")
async def get_chapter_store_mappings(
    user=Depends(get_verified_user)
):
    """
    모든 챕터-Store 매핑 조회 (store가 설정된 챕터만)
    """
    mappings = TextbookChapters.get_all_rag_store_mappings()
    return {"mappings": mappings}


@router.get("/chapter-mapping/{chapter_id}")
async def get_chapter_store_mapping(
    chapter_id: str,
    user=Depends(get_verified_user)
):
    """
    특정 챕터의 Store 매핑 조회
    """
    chapter = TextbookChapters.get_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if not chapter.rag_store_name:
        raise HTTPException(status_code=404, detail="No RAG store configured for this chapter")

    return {
        "store_name": chapter.rag_store_name,
        "display_name": chapter.title
    }


@router.delete("/chapter-mapping/{chapter_id}")
async def delete_chapter_store_mapping(
    chapter_id: str,
    user=Depends(get_admin_user)
):
    """
    챕터-Store 매핑 삭제 (관리자 전용)
    """
    chapter = TextbookChapters.set_rag_store(chapter_id, None)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return {"success": True, "message": f"Deleted RAG store mapping for {chapter_id}"}


# ============================================================
# RAG 쿼리 엔드포인트
# ============================================================

@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    request: Request,
    body: RAGQueryRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user)
):
    """
    RAG 쿼리 실행 (문서 검색 + 응답 생성)

    - **question**: 질문 내용
    - **store_names**: 검색할 Store 이름 목록
    - **model**: 사용할 Gemini 모델 (기본: gemini-2.5-flash)
    - **temperature**: 응답 다양성 (0.0 ~ 1.0, 기본: 0.2)
    - **system_instruction**: 시스템 지시사항 (선택)
    - **prompt_group_id**: 프롬프트 그룹 ID (선택)
    - **proficiency_level**: 난이도 레벨 (선택)
    - **response_style**: 응답 스타일 (선택)
    """
    service = get_rag_service(request)

    # Compose prompts with fallback logic
    log.info("="*80)
    log.info("[GEMINI RAG] 쿼리 요청 받음")
    log.info(f"  prompt_group_id: {body.prompt_group_id}")
    log.info(f"  system_instruction: {body.system_instruction[:50] if body.system_instruction else None}...")
    log.info(f"  proficiency_level: {body.proficiency_level}")
    log.info(f"  response_style: {body.response_style}")
    log.info(f"  DEFAULT_PROMPT_GROUP_ID: {getattr(request.app.state.config, 'DEFAULT_PROMPT_GROUP_ID', None)}")
    log.info("="*80)

    composed_system = compose_with_fallback(
        group_id=body.prompt_group_id,
        system_prompt=body.system_instruction,
        default_group_id=getattr(
            request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
        ),
        proficiency_level=body.proficiency_level,
        response_style=body.response_style,
    )

    final_system = composed_system if composed_system else body.system_instruction

    log.info("="*80)
    log.info("[GEMINI RAG] 최종 시스템 프롬프트:")
    log.info(f"  조합된 프롬프트 길이: {len(composed_system) if composed_system else 0} 문자")
    log.info(f"  최종 프롬프트 길이: {len(final_system) if final_system else 0} 문자")
    log.info(f"  내용: {final_system[:500] if final_system else '(없음)'}...")
    log.info("="*80)

    result = service.query(
        question=body.question,
        store_names=body.store_names,
        model=body.model,
        temperature=body.temperature,
        system_instruction=final_system
    )

    # 채팅 생성 및 제목 생성 로직
    chat_id = None  # 항상 새 채팅 생성

    # RAG 응답이 성공하면 새 채팅 생성
    if result.get("success") and result.get("text"):
        log.info("[GEMINI RAG] Creating new chat for RAG query")

        # 채팅 메시지 구조 생성
        chat_messages = {
            "title": "새 채팅",
            "messages": [
                {
                    "role": "user",
                    "content": body.question
                },
                {
                    "role": "assistant",
                    "content": result["text"]
                }
            ]
        }

        # 새 채팅 생성
        chat_form = ChatForm(
            chat=chat_messages,
            chapter_id=None,  # RAG query doesn't specify chapter
            proficiency_level=body.proficiency_level,
            response_style=body.response_style
        )

        new_chat = Chats.insert_new_chat(user.id, chat_form)
        if new_chat:
            chat_id = new_chat.id
            log.info(f"[GEMINI RAG] Created new chat: {chat_id}")
        else:
            log.error("[GEMINI RAG] Failed to create new chat")

    # 채팅 ID가 있으면 백그라운드에서 제목 생성
    enable_title_gen = getattr(request.app.state.config, 'ENABLE_TITLE_GENERATION', True)
    api_key = get_gemini_api_key(request)

    if chat_id and enable_title_gen and api_key:
        # 제목 생성용 메시지 준비
        messages = [
            {"role": "user", "content": body.question},
            {"role": "assistant", "content": result.get("text", "")}
        ]

        log.info(f"[GEMINI RAG] Scheduling title generation for chat {chat_id}")
        background_tasks.add_task(
            generate_chat_title_background,
            api_key,
            chat_id,
            messages,
            user.id
        )

    # 응답에 chat_id 포함
    response_data = {**result, "chat_id": chat_id}
    return RAGQueryResponse(**response_data)


@router.post("/query/by-chapter", response_model=RAGQueryResponse)
async def query_rag_by_chapter(
    request: Request,
    background_tasks: BackgroundTasks,
    chapter_id: str,
    question: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
    system_instruction: Optional[str] = None,
    prompt_group_id: Optional[str] = None,
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """
    챕터 ID로 RAG 쿼리 실행

    - **chapter_id**: 챕터 ID (예: "ch-1")
    - **question**: 질문 내용
    - **model**: 사용할 Gemini 모델
    - **temperature**: 응답 다양성
    - **system_instruction**: 시스템 지시사항 (선택)
    - **prompt_group_id**: 프롬프트 그룹 ID (선택)
    - **proficiency_level**: 난이도 레벨 (선택)
    - **response_style**: 응답 스타일 (선택)
    """
    store_name = TextbookChapters.get_rag_store(chapter_id)
    if not store_name:
        raise HTTPException(
            status_code=404,
            detail=f"No RAG store configured for chapter: {chapter_id}"
        )

    service = get_rag_service(request)

    # Compose prompts with fallback logic
    log.info("="*80)
    log.info("[GEMINI RAG BY CHAPTER] 쿼리 요청 받음")
    log.info(f"  chapter_id: {chapter_id}")
    log.info(f"  prompt_group_id: {prompt_group_id}")
    log.info(f"  system_instruction: {system_instruction[:50] if system_instruction else None}...")
    log.info(f"  proficiency_level: {proficiency_level}")
    log.info(f"  response_style: {response_style}")
    log.info(f"  DEFAULT_PROMPT_GROUP_ID: {getattr(request.app.state.config, 'DEFAULT_PROMPT_GROUP_ID', None)}")
    log.info("="*80)

    composed_system = compose_with_fallback(
        group_id=prompt_group_id,
        system_prompt=system_instruction,
        default_group_id=getattr(
            request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
        ),
        proficiency_level=proficiency_level,
        response_style=response_style,
    )

    final_system = composed_system if composed_system else system_instruction

    log.info("="*80)
    log.info("[GEMINI RAG BY CHAPTER] 최종 시스템 프롬프트:")
    log.info(f"  조합된 프롬프트 길이: {len(composed_system) if composed_system else 0} 문자")
    log.info(f"  최종 프롬프트 길이: {len(final_system) if final_system else 0} 문자")
    log.info(f"  내용: {final_system[:500] if final_system else '(없음)'}...")
    log.info("="*80)

    result = service.query(
        question=question,
        store_names=[store_name],
        model=model,
        temperature=temperature,
        system_instruction=final_system
    )

    # 채팅 생성 및 제목 생성 로직
    final_chat_id = None  # 항상 새 채팅 생성

    # RAG 응답이 성공하면 새 채팅 생성
    if result.get("success") and result.get("text"):
        log.info(f"[GEMINI RAG BY CHAPTER] Creating new chat for chapter {chapter_id}")

        # 채팅 메시지 구조 생성
        chat_messages = {
            "title": "새 채팅",
            "messages": [
                {
                    "role": "user",
                    "content": question
                },
                {
                    "role": "assistant",
                    "content": result["text"]
                }
            ]
        }

        # 새 채팅 생성
        chat_form = ChatForm(
            chat=chat_messages,
            chapter_id=chapter_id,
            proficiency_level=proficiency_level,
            response_style=response_style
        )

        new_chat = Chats.insert_new_chat(user.id, chat_form)
        if new_chat:
            final_chat_id = new_chat.id
            log.info(f"[GEMINI RAG BY CHAPTER] Created new chat: {final_chat_id}")
        else:
            log.error("[GEMINI RAG BY CHAPTER] Failed to create new chat")

    # 채팅 ID가 있으면 백그라운드에서 제목 생성
    enable_title_gen = getattr(request.app.state.config, 'ENABLE_TITLE_GENERATION', True)
    api_key = get_gemini_api_key(request)

    if final_chat_id and enable_title_gen and api_key:
        # 제목 생성용 메시지 준비
        title_messages = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": result.get("text", "")}
        ]

        log.info(f"[GEMINI RAG BY CHAPTER] Scheduling title generation for chat {final_chat_id}")
        background_tasks.add_task(
            generate_chat_title_background,
            api_key,
            final_chat_id,
            title_messages,
            user.id
        )

    # 응답에 chat_id 포함
    response_data = {**result, "chat_id": final_chat_id}
    return RAGQueryResponse(**response_data)


# ============================================================
# 헬스 체크
# ============================================================

@router.get("/health")
async def health_check(request: Request):
    """
    Gemini RAG 서비스 헬스 체크
    """
    api_key = get_gemini_api_key(request)
    if not api_key:
        return {
            "status": "error",
            "message": "Gemini API key not found. Please configure Gemini in OpenAI settings."
        }

    try:
        service = get_rag_service(request)
        stores = service.list_stores()
        mappings = TextbookChapters.get_all_rag_store_mappings()
        return {
            "status": "ok",
            "store_count": len(stores),
            "chapter_mappings": len(mappings)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
