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
from open_webui.utils.tool_gating import (
    execute_with_tool_gating,
    should_use_tool_gating,
    compose_stage2_system_prompt,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.textbooks import TextbookChapters
from open_webui.models.chats import Chats, ChatForm
from open_webui.models.models import Models

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
    enable_tool_gating: bool = True  # Enable two-stage tool gating by default


class RAGQueryResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    citations: List[dict] = []
    model: Optional[str] = None
    error: Optional[str] = None
    chat_id: Optional[str] = None  # Returned if a new chat was created
    used_tools: List[str] = []  # Tools used via tool gating
    tool_gating_stage: Optional[int] = None  # 1 or 2 (if tool gating was used)


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

        service = get_gemini_rag_service(api_key)

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

        # Gemini API 호출하여 제목 생성
        result = service.query(
            question=title_prompt,
            store_names=[],  # 제목 생성에는 RAG 불필요
            model="gemini-2.5-flash",
            temperature=0.7,
            system_instruction="You are a helpful assistant that generates concise chat titles."
        )

        if result.get("success") and result.get("text"):
            title = result["text"].strip()
            # 제목 정리 (따옴표, 특수문자 제거)
            title = title.replace('"', '').replace("'", '').strip()
            # 너무 길면 자르기
            if len(title) > 50:
                title = title[:47] + "..."

            # 채팅 제목 업데이트
            Chats.update_chat_title_by_id(chat_id, title)
            log.info(f"✅ Generated title for chat {chat_id}: {title}")
        else:
            log.warning(f"Failed to generate title for chat {chat_id}: {result.get('error')}")

    except Exception as e:
        log.error(f"Error generating title for chat {chat_id}: {e}")


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
    - **enable_tool_gating**: Tool gating 활성화 (기본: True)
    """
    service = get_rag_service(request)

    # Compose prompts with fallback logic (now returns tuple with tool_prompts)
    log.info("="*80)
    log.info("[GEMINI RAG] 쿼리 요청 받음")
    log.info(f"  prompt_group_id: {body.prompt_group_id}")
    log.info(f"  system_instruction: {body.system_instruction[:50] if body.system_instruction else None}...")
    log.info(f"  proficiency_level: {body.proficiency_level}")
    log.info(f"  response_style: {body.response_style}")
    log.info(f"  enable_tool_gating: {body.enable_tool_gating}")
    log.info(f"  DEFAULT_PROMPT_GROUP_ID: {getattr(request.app.state.config, 'DEFAULT_PROMPT_GROUP_ID', None)}")
    log.info("="*80)

    # Stage 1 프롬프트 (경량, base만 사용) - Tool gating용
    composed_gating, tool_prompts = compose_with_fallback(
        group_id=body.prompt_group_id,
        system_prompt=body.system_instruction,
        default_group_id=getattr(
            request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
        ),
        proficiency_level=body.proficiency_level,
        response_style=body.response_style,
        include_tools=False,
        use_only_base=True  # Stage 1: Base only (~55% token reduction)
    )

    # Stage 2 프롬프트 (전체, base + proficiency + style) - Actual execution용
    composed_full, _ = compose_with_fallback(
        group_id=body.prompt_group_id,
        system_prompt=body.system_instruction,
        default_group_id=getattr(
            request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
        ),
        proficiency_level=body.proficiency_level,
        response_style=body.response_style,
        include_tools=False,
        use_only_base=False  # Stage 2: Full prompt
    )

    gating_system = composed_gating if composed_gating else body.system_instruction
    final_system = composed_full if composed_full else body.system_instruction

    log.info("="*80)
    log.info("[GEMINI RAG] 최종 시스템 프롬프트:")
    log.info(f"  Stage 1 (gating) 프롬프트 길이: {len(gating_system) if gating_system else 0} 문자")
    log.info(f"  Stage 2 (execution) 프롬프트 길이: {len(final_system) if final_system else 0} 문자")
    log.info(f"  Tool prompts 개수: {len(tool_prompts)}")
    log.info(f"  Tool prompts: {[t.command for t in tool_prompts]}")
    log.info(f"  Stage 1 내용: {gating_system[:300] if gating_system else '(없음)'}...")
    log.info(f"  Stage 2 내용: {final_system[:300] if final_system else '(없음)'}...")
    log.info("="*80)

    # Determine if we should use tool gating
    used_tools = []
    tool_gating_stage = None

    if should_use_tool_gating(tool_prompts, body.enable_tool_gating):
        log.info("[GEMINI RAG] Using tool gating (two-stage)")

        # Look up model configuration to get tool_gating_model
        tool_gating_model = None
        model_config = Models.get_model_by_id(body.model)
        if model_config and model_config.meta:
            tool_gating_model = model_config.meta.tool_gating_model
            if tool_gating_model:
                log.info(f"[GEMINI RAG] Found tool_gating_model in config: {tool_gating_model}")
            else:
                log.info(f"[GEMINI RAG] No tool_gating_model configured, using main model for both stages")

        tool_gating_result = execute_with_tool_gating(
            query=body.question,
            base_system=gating_system or "",  # Stage 1: Lightweight prompt (base only)
            full_system=final_system or "",  # Stage 2: Full prompt (base + proficiency + style)
            tool_prompts=tool_prompts,
            llm_call_fn=service.query,
            gating_model=tool_gating_model,
            cache_gating_stage="gating",  # Enable global caching for Stage 1
            cache_execution_stage="execution",  # Enable global caching for Stage 2
            store_names=body.store_names,
            model=body.model,
            temperature=body.temperature,
        )
        result = {
            "success": True,
            "text": tool_gating_result.text,
            "citations": [],
            "model": body.model,
        }
        used_tools = tool_gating_result.used_tools
        tool_gating_stage = tool_gating_result.stage
        log.info(f"[GEMINI RAG] Tool gating completed - stage: {tool_gating_stage}, tools: {used_tools}")
    else:
        # Legacy mode: include all tool prompts in system instruction
        if tool_prompts:
            log.info("[GEMINI RAG] Tool gating disabled, including all tools")
            final_system = compose_stage2_system_prompt(final_system or "", tool_prompts)

        # CRITICAL: Run in thread pool to avoid blocking event loop (multi-user support)
        import asyncio
        result = await asyncio.to_thread(
            service.query,
            question=body.question,
            store_names=body.store_names,
            model=body.model,
            temperature=body.temperature,
            system_instruction=final_system,
            cache_stage="execution"  # Enable global caching for legacy mode
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

    # 응답에 chat_id와 tool gating 정보 포함
    response_data = {
        **result,
        "chat_id": chat_id,
        "used_tools": used_tools,
        "tool_gating_stage": tool_gating_stage,
    }
    return RAGQueryResponse(**response_data)


@router.post("/query/by-chapter", response_model=RAGQueryResponse)
async def query_rag_by_chapter(
    request: Request,
    background_tasks: BackgroundTasks,
    chapter_id: Optional[str],
    question: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
    system_instruction: Optional[str] = None,
    prompt_group_id: Optional[str] = None,
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
    enable_tool_gating: bool = True,
    user=Depends(get_verified_user)
):
    """
    챕터 ID로 RAG 쿼리 실행

    - **chapter_id**: 챕터 ID (예: "ch-1"), null이면 "general" 사용
    - **question**: 질문 내용
    - **model**: 사용할 Gemini 모델
    - **temperature**: 응답 다양성
    - **system_instruction**: 시스템 지시사항 (선택)
    - **prompt_group_id**: 프롬프트 그룹 ID (선택)
    - **proficiency_level**: 난이도 레벨 (선택)
    - **response_style**: 응답 스타일 (선택)
    - **enable_tool_gating**: Tool gating 활성화 (기본: True)
    """
    # Fallback to "general" if chapter_id is null or empty
    if not chapter_id or chapter_id.strip() == "" or chapter_id.lower() == "null":
        chapter_id = "general"
        log.info(f"[GEMINI RAG BY CHAPTER] chapter_id was null, using fallback: {chapter_id}")

    store_name = TextbookChapters.get_rag_store(chapter_id)
    if not store_name:
        raise HTTPException(
            status_code=404,
            detail=f"No RAG store configured for chapter: {chapter_id}"
        )

    service = get_rag_service(request)

    # Compose prompts with fallback logic (now returns tuple with tool_prompts)
    log.info("="*80)
    log.info("[GEMINI RAG BY CHAPTER] 쿼리 요청 받음")
    log.info(f"  chapter_id: {chapter_id}")
    log.info(f"  prompt_group_id: {prompt_group_id}")
    log.info(f"  system_instruction: {system_instruction[:50] if system_instruction else None}...")
    log.info(f"  proficiency_level: {proficiency_level}")
    log.info(f"  response_style: {response_style}")
    log.info(f"  enable_tool_gating: {enable_tool_gating}")
    log.info(f"  DEFAULT_PROMPT_GROUP_ID: {getattr(request.app.state.config, 'DEFAULT_PROMPT_GROUP_ID', None)}")
    log.info("="*80)

    # Stage 1 프롬프트 (경량, base만 사용) - Tool gating용
    composed_gating, tool_prompts = compose_with_fallback(
        group_id=prompt_group_id,
        system_prompt=system_instruction,
        default_group_id=getattr(
            request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
        ),
        proficiency_level=proficiency_level,
        response_style=response_style,
        include_tools=False,
        use_only_base=True  # Stage 1: Base only (~55% token reduction)
    )

    # Stage 2 프롬프트 (전체, base + proficiency + style) - Actual execution용
    composed_full, _ = compose_with_fallback(
        group_id=prompt_group_id,
        system_prompt=system_instruction,
        default_group_id=getattr(
            request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
        ),
        proficiency_level=proficiency_level,
        response_style=response_style,
        include_tools=False,
        use_only_base=False  # Stage 2: Full prompt
    )

    gating_system = composed_gating if composed_gating else system_instruction
    final_system = composed_full if composed_full else system_instruction

    log.info("="*80)
    log.info("[GEMINI RAG BY CHAPTER] 최종 시스템 프롬프트:")
    log.info(f"  Stage 1 (gating) 프롬프트 길이: {len(gating_system) if gating_system else 0} 문자")
    log.info(f"  Stage 2 (execution) 프롬프트 길이: {len(final_system) if final_system else 0} 문자")
    log.info(f"  Tool prompts 개수: {len(tool_prompts)}")
    log.info(f"  Tool prompts: {[t.command for t in tool_prompts]}")
    log.info(f"  Stage 1 내용: {gating_system[:300] if gating_system else '(없음)'}...")
    log.info(f"  Stage 2 내용: {final_system[:300] if final_system else '(없음)'}...")
    log.info("="*80)

    # Determine if we should use tool gating
    used_tools = []
    tool_gating_stage = None

    if should_use_tool_gating(tool_prompts, enable_tool_gating):
        log.info("[GEMINI RAG BY CHAPTER] Using tool gating (two-stage)")

        # Look up model configuration to get tool_gating_model
        tool_gating_model = None
        model_config = Models.get_model_by_id(model)
        if model_config and model_config.meta:
            tool_gating_model = model_config.meta.tool_gating_model
            if tool_gating_model:
                log.info(f"[GEMINI RAG BY CHAPTER] Found tool_gating_model in config: {tool_gating_model}")
            else:
                log.info(f"[GEMINI RAG BY CHAPTER] No tool_gating_model configured, using main model for both stages")

        tool_gating_result = execute_with_tool_gating(
            query=question,
            base_system=gating_system or "",  # Stage 1: Lightweight prompt (base only)
            full_system=final_system or "",  # Stage 2: Full prompt (base + proficiency + style)
            tool_prompts=tool_prompts,
            llm_call_fn=service.query,
            gating_model=tool_gating_model,
            cache_gating_stage="gating",  # Enable global caching for Stage 1
            cache_execution_stage="execution",  # Enable global caching for Stage 2
            store_names=[store_name],
            model=model,
            temperature=temperature,
        )
        result = {
            "success": True,
            "text": tool_gating_result.text,
            "citations": [],
            "model": model,
        }
        used_tools = tool_gating_result.used_tools
        tool_gating_stage = tool_gating_result.stage
        log.info(f"[GEMINI RAG BY CHAPTER] Tool gating completed - stage: {tool_gating_stage}, tools: {used_tools}")
    else:
        # Legacy mode: include all tool prompts in system instruction
        if tool_prompts:
            log.info("[GEMINI RAG BY CHAPTER] Tool gating disabled, including all tools")
            final_system = compose_stage2_system_prompt(final_system or "", tool_prompts)

        # CRITICAL: Run in thread pool to avoid blocking event loop (multi-user support)
        import asyncio
        result = await asyncio.to_thread(
            service.query,
            question=question,
            store_names=[store_name],
            model=model,
            temperature=temperature,
            system_instruction=final_system,
            cache_stage="execution"  # Enable global caching for legacy mode
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

    # 응답에 chat_id와 tool gating 정보 포함
    response_data = {
        **result,
        "chat_id": final_chat_id,
        "used_tools": used_tools,
        "tool_gating_stage": tool_gating_stage,
    }
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


# ============================================================
# 캐시 관리 API
# ============================================================

@router.get("/cache/stats")
async def get_cache_stats(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Get global cache statistics.

    Admin only endpoint to monitor cache usage.

    Returns:
        - total_caches: Total number of cached contents
        - max_caches: Maximum allowed caches
        - by_stage: Count of caches by stage (gating/execution)
        - by_model: Count of caches by model ID
        - tool_spec_version: Current tool spec version
    """
    api_key = get_gemini_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not found. Please configure Gemini in OpenAI settings."
        )

    try:
        service = get_rag_service(request)
        stats = service.cache_manager.get_stats()

        return {
            "status": "ok",
            **stats
        }
    except Exception as e:
        log.error(f"[CACHE] Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.delete("/cache")
async def clear_all_caches(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Clear all cached system prompts.

    Admin only endpoint. Use this when you modify prompts and want to
    force cache regeneration.

    Returns:
        - deleted_count: Number of caches successfully deleted
        - failed_count: Number of caches that failed to delete
        - errors: List of error messages (if any)
    """
    api_key = get_gemini_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not found. Please configure Gemini in OpenAI settings."
        )

    try:
        service = get_rag_service(request)
        result = service.cache_manager.clear_all_caches()

        return {
            "status": "ok",
            **result
        }
    except Exception as e:
        log.error(f"[CACHE] Failed to clear all caches: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear caches: {str(e)}"
        )


@router.delete("/cache/{stage}")
async def clear_caches_by_stage(
    request: Request,
    stage: str,
    user=Depends(get_admin_user)
):
    """
    Clear caches for a specific stage.

    Admin only endpoint. Clears only caches for the specified stage
    (gating or execution).

    Args:
        stage: Stage to clear ("gating" or "execution")

    Returns:
        - stage: The stage that was cleared
        - deleted_count: Number of caches successfully deleted
        - failed_count: Number of caches that failed to delete
        - errors: List of error messages (if any)
    """
    if stage not in ("gating", "execution"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage}. Must be 'gating' or 'execution'"
        )

    api_key = get_gemini_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not found. Please configure Gemini in OpenAI settings."
        )

    try:
        service = get_rag_service(request)
        result = service.cache_manager.clear_caches_by_stage(stage)

        return {
            "status": "ok",
            **result
        }
    except Exception as e:
        log.error(f"[CACHE] Failed to clear caches for stage {stage}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear caches for stage {stage}: {str(e)}"
        )
