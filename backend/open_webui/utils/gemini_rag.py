"""
Gemini File Search RAG 유틸리티 모듈

Google Gemini의 File Search 기능을 사용하여 RAG(Retrieval-Augmented Generation)를 구현합니다.
"""

import logging
import time
from typing import Optional, List, Dict, Any

from google import genai
from google.genai import types

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class GeminiRAGService:
    """Gemini File Search RAG 서비스 클래스"""

    def __init__(self, api_key: str):
        """
        GeminiRAGService 초기화

        Args:
            api_key: Google AI Studio API 키
        """
        self.client = genai.Client(api_key=api_key)
        self._stores_cache: Dict[str, Any] = {}

    # ============================================================
    # Store (코퍼스) 관리
    # ============================================================

    def create_store(self, display_name: str) -> Dict[str, Any]:
        """
        새로운 File Search Store(코퍼스) 생성

        Args:
            display_name: Store 표시 이름 (예: "Chapter 1 - ODEs")

        Returns:
            생성된 Store 정보
        """
        try:
            store = self.client.file_search_stores.create(
                config={"display_name": display_name}
            )
            log.info(f"Created store: {store.name} ({display_name})")
            return {
                "name": store.name,
                "display_name": display_name,
                "success": True
            }
        except Exception as e:
            log.error(f"Failed to create store: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_stores(self) -> List[Dict[str, Any]]:
        """
        모든 Store 목록 조회

        Returns:
            Store 목록
        """
        try:
            stores = list(self.client.file_search_stores.list())
            return [
                {
                    "name": store.name,
                    "display_name": getattr(store, "display_name", "Unknown"),
                    "create_time": getattr(store, "create_time", None),
                }
                for store in stores
            ]
        except Exception as e:
            log.error(f"Failed to list stores: {e}")
            return []

    def get_store(self, store_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 Store 정보 조회

        Args:
            store_name: Store 이름 (예: "fileSearchStores/xxx")

        Returns:
            Store 정보 또는 None
        """
        try:
            store = self.client.file_search_stores.get(name=store_name)
            return {
                "name": store.name,
                "display_name": getattr(store, "display_name", "Unknown"),
                "create_time": getattr(store, "create_time", None),
            }
        except Exception as e:
            log.error(f"Failed to get store {store_name}: {e}")
            return None

    def delete_store(self, store_name: str) -> bool:
        """
        Store 삭제

        Args:
            store_name: Store 이름

        Returns:
            삭제 성공 여부
        """
        try:
            self.client.file_search_stores.delete(name=store_name)
            log.info(f"Deleted store: {store_name}")
            return True
        except Exception as e:
            log.error(f"Failed to delete store {store_name}: {e}")
            return False

    def list_files(self, store_name: str, api_key: str = None) -> List[Dict[str, Any]]:
        """
        Store 내 파일(문서) 목록 조회

        Args:
            store_name: Store 이름 (예: "fileSearchStores/xxx")
            api_key: API 키 (REST API 호출용)

        Returns:
            파일 목록
        """
        import requests

        try:
            # REST API 직접 호출 (SDK보다 안정적)
            url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}/documents"
            headers = {"x-goog-api-key": api_key} if api_key else {}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                documents = data.get("documents", [])
                return [
                    {
                        "name": doc.get("name", "Unknown"),
                        "display_name": doc.get("displayName", doc.get("name", "Unknown")),
                        "create_time": doc.get("createTime"),
                        "update_time": doc.get("updateTime"),
                        "state": doc.get("state"),
                        "size_bytes": doc.get("sizeBytes"),
                        "mime_type": doc.get("mimeType"),
                    }
                    for doc in documents
                ]
            else:
                log.error(f"Failed to list files: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            log.error(f"Failed to list files in store {store_name}: {e}")
            return []

    # ============================================================
    # 파일 업로드
    # ============================================================

    def upload_file(
        self,
        file_path: str,
        store_name: str,
        max_tokens_per_chunk: int = 400,
        max_overlap_tokens: int = 40,
        wait_for_completion: bool = True,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        파일을 Store에 업로드 (자동 청킹 및 임베딩)

        Args:
            file_path: 업로드할 파일 경로
            store_name: 대상 Store 이름
            max_tokens_per_chunk: 청크당 최대 토큰 수 (기본: 400)
            max_overlap_tokens: 청크 간 오버랩 토큰 수 (기본: 40)
            wait_for_completion: 업로드 완료까지 대기 여부
            timeout_seconds: 타임아웃 (초)

        Returns:
            업로드 결과
        """
        try:
            operation = self.client.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=store_name,
                config={
                    "chunking_config": {
                        "white_space_config": {
                            "max_tokens_per_chunk": max_tokens_per_chunk,
                            "max_overlap_tokens": max_overlap_tokens
                        }
                    }
                }
            )

            if wait_for_completion:
                start_time = time.time()
                while not operation.done:
                    if time.time() - start_time > timeout_seconds:
                        return {
                            "success": False,
                            "error": "Upload timeout"
                        }
                    time.sleep(5)
                    operation = self.client.operations.get(operation)

            log.info(f"Uploaded file to {store_name}: {file_path}")
            return {
                "success": True,
                "operation_name": operation.name,
                "done": operation.done
            }
        except Exception as e:
            log.error(f"Failed to upload file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def upload_file_bytes(
        self,
        file_content: bytes,
        file_name: str,
        store_name: str,
        max_tokens_per_chunk: int = 400,
        max_overlap_tokens: int = 40,
        wait_for_completion: bool = True,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        파일 바이트를 Store에 업로드

        Args:
            file_content: 파일 내용 (bytes)
            file_name: 파일 이름
            store_name: 대상 Store 이름
            max_tokens_per_chunk: 청크당 최대 토큰 수
            max_overlap_tokens: 청크 간 오버랩 토큰 수
            wait_for_completion: 업로드 완료까지 대기 여부
            timeout_seconds: 타임아웃 (초)

        Returns:
            업로드 결과
        """
        import tempfile
        import os

        try:
            # 임시 파일 생성
            suffix = os.path.splitext(file_name)[1] or ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name

            # 업로드 수행
            result = self.upload_file(
                file_path=tmp_path,
                store_name=store_name,
                max_tokens_per_chunk=max_tokens_per_chunk,
                max_overlap_tokens=max_overlap_tokens,
                wait_for_completion=wait_for_completion,
                timeout_seconds=timeout_seconds
            )

            # 임시 파일 삭제
            os.unlink(tmp_path)

            return result
        except Exception as e:
            log.error(f"Failed to upload file bytes: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # ============================================================
    # RAG 쿼리
    # ============================================================

    def query(
        self,
        question: str,
        store_names: List[str],
        model: str = "gemini-2.5-flash",
        temperature: float = 0.2,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        RAG 쿼리 실행 (문서 검색 + 응답 생성)

        Args:
            question: 질문 내용
            store_names: 검색할 Store 이름 목록
            model: 사용할 Gemini 모델
            temperature: 응답 다양성 (0.0 ~ 1.0)
            system_instruction: 시스템 지시사항

        Returns:
            응답 결과
        """
        try:
            # Normalize store names to ensure they have the correct prefix
            normalized_store_names = []
            for name in store_names:
                if name and not name.startswith("fileSearchStores/"):
                    normalized_name = f"fileSearchStores/{name}"
                    log.warning(f"[GEMINI RAG QUERY] ⚠️  Store 이름 정규화: '{name}' → '{normalized_name}'")
                    normalized_store_names.append(normalized_name)
                else:
                    normalized_store_names.append(name)

            log.info("="*80)
            log.info("[GEMINI RAG QUERY] RAG 쿼리 시작")
            log.info(f"  질문: {question[:100]}...")
            log.info(f"  모델: {model}")
            log.info(f"  Temperature: {temperature}")
            log.info(f"  원본 Store Names: {store_names}")
            log.info(f"  정규화된 Store Names: {normalized_store_names}")
            log.info(f"  Store Names 길이: {len(normalized_store_names) if normalized_store_names else 0}")
            if normalized_store_names:
                for i, name in enumerate(normalized_store_names):
                    log.info(f"    [{i}] '{name}' (길이: {len(name) if name else 0})")
            log.info(f"  System Instruction 길이: {len(system_instruction) if system_instruction else 0}")
            log.info("="*80)

            config = types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=normalized_store_names
                        )
                    )
                ],
                temperature=temperature
            )

            if system_instruction:
                config.system_instruction = system_instruction

            log.info("[GEMINI RAG QUERY] Gemini API 호출 중...")
            response = self.client.models.generate_content(
                model=model,
                contents=question,
                config=config
            )
            log.info("[GEMINI RAG QUERY] ✅ 응답 받음")

            # 출처 정보 추출
            citations = []
            if hasattr(response, "grounding_metadata") and response.grounding_metadata:
                for citation in getattr(response.grounding_metadata, "citations", []):
                    citations.append({
                        "source": getattr(citation, "source", "Unknown"),
                        "start_index": getattr(citation, "start_index", None),
                        "end_index": getattr(citation, "end_index", None)
                    })

            return {
                "success": True,
                "text": response.text,
                "citations": citations,
                "model": model
            }
        except Exception as e:
            log.error("="*80)
            log.error(f"[GEMINI RAG QUERY] ❌ 에러 발생!")
            log.error(f"  에러 타입: {type(e).__name__}")
            log.error(f"  에러 메시지: {e}")
            log.error(f"  원본 store_names: {store_names}")
            log.error(f"  정규화된 store_names: {normalized_store_names if 'normalized_store_names' in locals() else 'N/A'}")
            log.error(f"  질문: {question[:100]}...")
            log.error("="*80)
            return {
                "success": False,
                "error": str(e)
            }

    def generate_with_rag(
        self,
        messages: List[Dict[str, str]],
        store_names: List[str],
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        대화 컨텍스트와 함께 RAG 응답 생성

        Args:
            messages: 대화 메시지 목록 [{"role": "user/assistant", "content": "..."}]
            store_names: 검색할 Store 이름 목록
            model: 사용할 Gemini 모델
            temperature: 응답 다양성
            system_instruction: 시스템 지시사항

        Returns:
            응답 결과
        """
        try:
            # Normalize store names to ensure they have the correct prefix
            normalized_store_names = []
            for name in store_names:
                if name and not name.startswith("fileSearchStores/"):
                    normalized_name = f"fileSearchStores/{name}"
                    log.warning(f"[GEMINI RAG] ⚠️  Store 이름 정규화: '{name}' → '{normalized_name}'")
                    normalized_store_names.append(normalized_name)
                else:
                    normalized_store_names.append(name)

            # 메시지를 Gemini 형식으로 변환
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg["content"])]
                    )
                )

            config = types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=normalized_store_names
                        )
                    )
                ],
                temperature=temperature
            )

            if system_instruction:
                config.system_instruction = system_instruction

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

            # 출처 정보 추출
            citations = []
            if hasattr(response, "grounding_metadata") and response.grounding_metadata:
                for citation in getattr(response.grounding_metadata, "citations", []):
                    citations.append({
                        "source": getattr(citation, "source", "Unknown"),
                        "start_index": getattr(citation, "start_index", None),
                        "end_index": getattr(citation, "end_index", None)
                    })

            return {
                "success": True,
                "text": response.text,
                "citations": citations,
                "model": model
            }
        except Exception as e:
            log.error(f"Failed to generate with RAG: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# ============================================================
# 싱글톤 인스턴스 관리
# ============================================================

_rag_service: Optional[GeminiRAGService] = None


def get_gemini_rag_service(api_key: str) -> GeminiRAGService:
    """
    GeminiRAGService 싱글톤 인스턴스 반환

    Args:
        api_key: Google AI Studio API 키

    Returns:
        GeminiRAGService 인스턴스
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = GeminiRAGService(api_key)
    return _rag_service


def reset_gemini_rag_service():
    """GeminiRAGService 인스턴스 리셋"""
    global _rag_service
    _rag_service = None
