#25.5.21 upstage solar llm으로 교체
#25.5.27 기존 버전에 6.11에서 추가된 BM25 변수 추가
#25.5.29 gemini 2.5 flash 모델로 수정
import logging
import os
import re  # 정규표현식 모듈 추가
import json
from typing import Optional, Union

import asyncio
import requests
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from huggingface_hub import snapshot_download
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from open_webui.config import VECTOR_DB
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

from open_webui.models.users import UserModel
from open_webui.models.files import Files

from open_webui.retrieval.vector.main import GetResult


from open_webui.env import (
    SRC_LOG_LEVELS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from open_webui.config import (
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


from typing import Any, Dict, List, Tuple

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever

load_dotenv()
OPENAI_API_KEY = os.getenv("upstageapikey", "AIzaSyCbqxkKfTCtZib1RbHjFbH9S0jJu56GgyQ")

async def process_queries_async(queries: List[str], openai_key: Optional[str] = None) -> List[str]:
    """여러 쿼리를 병렬로 처리하는 비동기 함수"""
    api_key = openai_key or OPENAI_API_KEY
    
    if not api_key:
        log.warning("OpenAI API 키가 설정되지 않았습니다. 쿼리 처리를 건너뜁니다.")
        return queries
    
    # 모든 비동기 작업을 모아서 한 번에 실행
    async def process_single_query(query: str) -> Tuple[str, List[str]]:
        # 1. 의학 약어 확장
        expanded_query = await expand_medical_abbreviation(query, api_key)
        
        # 2. 쿼리 향상
        enhanced_queries = await enhance_query(expanded_query, api_key)
        
        return expanded_query, enhanced_queries
    
    # 모든 쿼리에 대한 작업 생성
    tasks = [process_single_query(query) for query in queries]
    
    # 모든 작업 병렬 실행
    results = await asyncio.gather(*tasks)
    
    # 결과 처리
    all_queries = []
    for i, result in enumerate(results):
        original_query = queries[i] # 해당 결과에 대한 원본 쿼리 가져오기

        # 원본 쿼리 추가
        all_queries.append(original_query)

        if isinstance(result, Exception):
            # gather에서 예외가 발생한 경우 로그 기록 (이미 process_single_query에서 처리했을 수 있음)
            log.error(f"Task for query '{original_query}' failed with exception: {result}")
            # 실패한 경우 향상된 쿼리는 추가하지 않음
        elif result:
            # 성공적인 결과 처리 (expanded_query는 사용하지 않음)
            _, enhanced_queries = result
            # 향상된 쿼리들 추가
            all_queries.extend(enhanced_queries)
        else:
             # 결과가 비어있는 예외적인 경우 (process_single_query에서 빈 결과를 반환한 경우)
             log.warning(f"No results returned for query '{original_query}'")


    # 중복 제거 (선택 사항): 원본 쿼리가 향상된 쿼리 결과와 동일할 수 있음
    # 순서를 유지하면서 중복 제거
    seen = set()
    unique_queries = []
    for q in all_queries:
        if q not in seen:
            unique_queries.append(q)
            seen.add(q)

    return unique_queries

class VectorSearchRetriever(BaseRetriever):
    collection_name: Any
    embedding_function: Any
    top_k: int

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        result = VECTOR_DB_CLIENT.search(
            collection_name=self.collection_name,
            vectors=[self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)],
            limit=self.top_k,
        )

        ids = result.ids[0]
        metadatas = result.metadatas[0]
        documents = result.documents[0]

        results = []
        for idx in range(len(ids)):
            results.append(
                Document(
                    metadata=metadatas[idx],
                    page_content=documents[idx],
                )
            )
        return results


def query_doc(
    collection_name: str, query_embedding: list[float], k: int, user: UserModel = None
):
    try:
        log.debug(f"query_doc:doc {collection_name}")
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        log.exception(f"Error querying doc {collection_name} with limit {k}: {e}")
        raise e


def get_doc(collection_name: str, user: UserModel = None):
    try:
        log.debug(f"get_doc:doc {collection_name}")
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        log.exception(f"Error getting doc {collection_name}: {e}")
        raise e

async def expand_medical_abbreviation(query: str, openai_key: Optional[str] = None) -> str:
    """의학 약어를 full term으로 변환하는 함수"""
    # OpenAI API 키 설정 (인자로 전달받지 않으면 환경 변수 사용)
    api_key = openai_key or OPENAI_API_KEY
    
    if not api_key:
        log.warning("OpenAI API 키가 설정되지 않았습니다. 의학 약어 확장을 건너뜁니다.")
        return query
        
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "gemini-2.5-flash-preview-05-20",
                "reasoning_effort": "none",
                "messages": [
                    {"role": "system", "content": """당신은 한국표준질병사인분류(KCD, Korean Classification of Diseases) 진단 코드 및 의학용어(의학약어) 전문가입니다.
주어진 의료 약어(영문 또는 국문)에 대해 KCD 진단 코드의 맥락에서 가장 일반적으로 사용되는 공식적인 풀네임(Full term)만 반환하세요.

약어가 여러 의미를 가질 수 있을 때는 가장 흔히 사용되는 진단명을 기준으로 반환합니다.
약어가 아니라 문장 형태의 입력이 들어오면 입력된 내용을 그대로 반환합니다.
아무 입력도 없으면 빈 문자열을 반환합니다.
추가적인 설명이나 문장은 포함하지 마십시오.
입력된 값이 이미지의 백터 값등 상당히 긴 문자열의 나열일 경우에는 아무것도 반환하지않습니다

예시:
입력:
MM
출력:
Multiple Myeloma

입력:
AKI
출력:
Acute Kidney Injury

입력:
DM
출력:
Diabetes Mellitus

입력:
pcp
출력:
Pneumocystis Pneumonia

입력:
pjp
출력:
Pneumocystis jirovecii pneumonia

입력:
hCCA
출력:
Hilar Cholangiocarcinoma

입력:
Not a medical term
출력:
Not a medical term

입력:
"" (empty input)
출력:
"" (empty input)

입력:
soft tissue cancer의 skin invasion의 seer코드 알려줘
출력:
soft tissue cancer의 skin invasion의 seer코드 알려줘

입력:
+16Tc6Y8OjWCWcNpbF9ssU8DKAdrqu44XGBwOKzfgv8AHC88J/Bv4p+DNK8HJrkWuTRXv237J5ttaRSZQvdqVbcIcK0ZGNrc8cUhc5ag8afAq3/ZNbRD4LuJvElxqr20upXCbo4tSCht8d0o3RoYcBYyBmofiP8AEv4W6h+~
출력:
"" (empty input)
"""},
                    {"role": "user", "content": query}
                ],
                "temperature": 0
            }
        )
        response.raise_for_status()
        expanded_term = response.json()["choices"][0]["message"]["content"].strip()
        log.info(f"Medical abbreviation expansion: '{query}' -> '{expanded_term}'")
        return expanded_term
    except Exception as e:
        log.error(f"Error expanding medical abbreviation: {e}")
        return query


async def enhance_query(query: str, openai_key: Optional[str] = None) -> list[str]:
    """쿼리를 분석하고 확장하여 더 정확한 검색 결과를 얻기 위한 함수
    
    1. 원본 쿼리 유지
    2. 동의어/유사어 추가
    """
    # OpenAI API 키 설정 (인자로 전달받지 않으면 환경 변수 사용)
    api_key = openai_key or OPENAI_API_KEY
    
    if not api_key:
        log.warning("OpenAI API 키가 설정되지 않았습니다. 쿼리 향상을 건너뜁니다.")
        return [query]
        
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "gemini-2.5-flash-preview-05-20",
                "reasoning_effort": "none",
                "messages": [
                    {"role": "system", "content": """당신은 의학 및 일반 검색 쿼리 향상 전문가입니다.
주어진 검색 쿼리를 분석하여 검색 성능을 높이기 위한 다양한 변형 쿼리를 생성하세요.
다음 2가지 타입의 쿼리를 반환하세요:
1. original: 원본 쿼리 그대로
2. synonyms: 동의어나 유사어를 포함한 쿼리를 1개만 생성(원본쿼리가 한국어라면 영어로 동의어나 유사어, 원본쿼리가 영어라면 한국어로 동의어나 유사어 생성, 원본쿼리에 의학약어가 있다면 full term으로 변환 후 생성)

예시:
입력: "Acute Kidney Injury"
출력:
{
  "original": "Acute Kidney Injury",
  "synonyms": "급성신손상"
}
"""},
                    {"role": "user", "content": query}
                ],
                "temperature": 0
            }
        )
        response.raise_for_status()
        content_from_api = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content_from_api, re.DOTALL)
        if match:
            json_string = match.group(1)
        else:
            json_string = content_from_api
        result = json_string.strip()
        parsed_result = json.loads(result)
        enhanced_queries = [
            parsed_result["original"],
            parsed_result["synonyms"]
        ]
        log.info(f"Enhanced queries: {enhanced_queries}")
        return enhanced_queries
    except Exception as e:
        log.error(f"Error enhancing query: {e}")
        return [query]  # 오류 발생 시 원본 쿼리만 반환

def query_doc_with_hybrid_search(
    collection_name: str,
    collection_result: GetResult,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
    openai_key: Optional[str] = None,
    bm25_weight: float = 0.3,
    vector_weight: float = 0.7,
) -> dict:
    
    api_key = openai_key or OPENAI_API_KEY
    
    try:
        log.debug(f"query_doc_with_hybrid_search:doc {collection_name}")
        adjusted_weights = adjust_search_weights(query, bm25_weight, vector_weight)
        
        bm25_retriever = BM25Retriever.from_texts(
            texts=collection_result.documents[0],
            metadatas=collection_result.metadatas[0],
        )
        bm25_retriever.k = k

        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_search_retriever], 
            weights=[adjusted_weights["bm25"], adjusted_weights["vector"]]
        )
        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k_reranker,
            reranking_function=None,
            r_score=r,
            openai_key=api_key,
            use_llm_reranking=True,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = compression_retriever.invoke(query)

        distances = [d.metadata.get("score") for d in result]
        documents = [d.page_content for d in result]
        metadatas = [d.metadata for d in result]

        # retrieve only min(k, k_reranker) items, sort and cut by distance if k < k_reranker
        if k < k_reranker:
            sorted_items = sorted(
                zip(distances, metadatas, documents), key=lambda x: x[0], reverse=True
            )
            sorted_items = sorted_items[:k]
            distances, documents, metadatas = map(list, zip(*sorted_items))

        result = {
            "distances": [distances],
            "documents": [documents],
            "metadatas": [metadatas],
        }

        log.info(
            "query_doc_with_hybrid_search:result "
            + f'{result["metadatas"]} {result["distances"]}'
        )
        return result
    except Exception as e:
        log.exception(f"Error querying doc {collection_name} with hybrid search: {e}")
        raise e

def adjust_search_weights(query: str, default_bm25_weight: float, default_vector_weight: float) -> dict:
    """쿼리 특성에 따라 검색 가중치를 동적으로 조정하는 함수"""
    # 기본 가중치
    weights = {
        "bm25": default_bm25_weight,
        "vector": default_vector_weight
    }
    
    # 쿼리 길이
    query_length = len(query.split())
    
    # 특수 문자 포함 여부
    has_special_chars = any(char in query for char in "{}[]()\"':;,.<>/?\\|!@#$%^&*-_=+~`")
    
    # 숫자 포함 여부
    has_numbers = any(char.isdigit() for char in query)
    
    # 쿼리 특성에 따른 가중치 조정
    if query_length <= 3:  # 짧은 쿼리: 정확한 키워드 매칭이 중요하므로 BM25 가중치 증가
        weights["bm25"] = min(default_bm25_weight + 0.2, 0.6)
        weights["vector"] = 1.0 - weights["bm25"]
    elif query_length >= 8:  # 긴 쿼리: 의미적 유사성이 중요하므로 벡터 가중치 증가
        weights["vector"] = min(default_vector_weight + 0.1, 0.8)
        weights["bm25"] = 1.0 - weights["vector"]
    
    # 특수 문자나 숫자가 있으면 정확한 매칭이 중요하므로 BM25 가중치 증가
    if has_special_chars or has_numbers:
        weights["bm25"] = min(weights["bm25"] + 0.15, 0.7)
        weights["vector"] = 1.0 - weights["bm25"]
    
    # 가중치 합이 1이 되도록 정규화
    total = weights["bm25"] + weights["vector"]
    weights["bm25"] /= total
    weights["vector"] /= total
    
    log.info(f"Adjusted search weights for query '{query}': {weights}")
    return weights

def merge_get_results(get_results: list[dict]) -> dict:
    # Initialize lists to store combined data
    combined_documents = []
    combined_metadatas = []
    combined_ids = []

    for data in get_results:
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])
        combined_ids.extend(data["ids"][0])

    # Create the output dictionary
    result = {
        "documents": [combined_documents],
        "metadatas": [combined_metadatas],
        "ids": [combined_ids],
    }

    return result


def merge_and_sort_query_results(query_results: list[dict], k: int, diversity_threshold: float = 0.8) -> dict:
    # Initialize lists to store combined data
    combined = dict()  # To store documents with unique document hashes

    for data in query_results:
        distances = data["distances"][0]
        documents = data["documents"][0]
        metadatas = data["metadatas"][0]

        for distance, document, metadata in zip(distances, documents, metadatas):
            if isinstance(document, str):
                doc_hash = hashlib.sha256(
                    document.encode()
                ).hexdigest()  # Compute a hash for uniqueness

                if doc_hash not in combined.keys():
                    combined[doc_hash] = (distance, document, metadata)
                    continue  # if doc is new, no further comparison is needed

                # if doc is alredy in, but new distance is better, update
                if distance > combined[doc_hash][0]:
                    combined[doc_hash] = (distance, document, metadata)

    combined = list(combined.values())
    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=True)

    if not combined:
        sorted_distances = []
        sorted_documents = []
        sorted_metadatas = []
    else:
        # 결과 다양성 향상을 위한 처리
        diversified_results = apply_maximal_marginal_relevance(combined, k, diversity_threshold)
        
        # Unzip the diversified list
        sorted_distances, sorted_documents, sorted_metadatas = zip(*diversified_results)

        # 리스트로 변환
        sorted_distances = list(sorted_distances)
        sorted_documents = list(sorted_documents)
        sorted_metadatas = list(sorted_metadatas)

    # Create the output dictionary
    result = {
        "distances": [sorted_distances],
        "documents": [sorted_documents],
        "metadatas": [sorted_metadatas],
    }
    
    return result

def apply_maximal_marginal_relevance(
    combined_results: list[tuple], 
    k: int, 
    diversity_threshold: float = 0.8
) -> list[tuple]:
    """
    결과의 다양성을 높이기 위해 개선된 Maximal Marginal Relevance 알고리즘 적용
    
    Args:
        combined_results: (score, document, metadata) 튜플 리스트
        k: 반환할 최대 결과 수
        diversity_threshold: 다양성 임계값 (0에 가까울수록 다양성 증가, 1에 가까울수록 원래 순위 유지)
    
    Returns:
        다양성이 개선된 결과 리스트
    """
    if len(combined_results) <= 1 or k <= 1:
        return combined_results[:k]
    
    # 이미 선택된 결과와 후보 결과 분리
    selected_results = [combined_results[0]]  # 첫 번째 결과는 항상 포함
    candidates = combined_results[1:]
    
    # 문서 텍스트 추출
    doc_contents = [doc for _, doc, _ in combined_results]
    
    # 벡터화 프로세스
    doc_vectors = []
    
    try:
        # 먼저 내장된 간단한 벡터화 방법 시도 (TF-IDF 벡터화 없이)
        for doc in doc_contents:
            # 간단한 BoW(Bag of Words) 벡터 계산
            words = doc.lower().split()
            word_counts = {}
            for word in words:
                if len(word) > 1:  # 짧은 단어 무시
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # 정규화된 벡터 생성
            total_words = sum(word_counts.values())
            if total_words > 0:
                normalized_vector = {word: count/total_words for word, count in word_counts.items()}
            else:
                normalized_vector = {}
                
            doc_vectors.append(normalized_vector)
            
    except Exception as e:
        log.error(f"Simple vectorization failed: {e}")
        # 실패하면 대체 벡터화
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # 벡터화 인스턴스 사용
            tfidf_vectorizer = TfidfVectorizer()
            doc_vectors = tfidf_vectorizer.fit_transform(doc_contents).toarray()
        except Exception as e:
            log.error(f"TfidfVectorizer failed too: {e}")
            # 마지막 대안: 직접 문자열 유사도 계산 (자카드 유사도)
            for doc in doc_contents:
                words = set(doc.lower().split())
                doc_vectors.append(words)
    
    # MMR 알고리즘으로 다양성 있는 결과 선택
    while len(selected_results) < k and candidates:
        best_score = float('-inf')
        best_idx = -1
        
        for i, candidate in enumerate(candidates):
            candidate_idx = combined_results.index(candidate)
            original_score = candidate[0]  # 원래 유사도 점수
            
            # 이미 선택된 문서와의 최대 유사도 계산
            max_similarity = 0
            for selected in selected_results:
                selected_idx = combined_results.index(selected)
                
                # 벡터 유형에 따른 유사도 계산
                similarity = 0
                
                if isinstance(doc_vectors[0], dict):
                    # BoW 벡터인 경우 (dict)
                    v1 = doc_vectors[candidate_idx]
                    v2 = doc_vectors[selected_idx]
                    
                    # 코사인 유사도 계산
                    common_words = set(v1.keys()) & set(v2.keys())
                    if not common_words:
                        similarity = 0
                    else:
                        numerator = sum(v1[word] * v2[word] for word in common_words)
                        sum1 = sum(val**2 for val in v1.values())
                        sum2 = sum(val**2 for val in v2.values())
                        denominator = (sum1**0.5) * (sum2**0.5)
                        if denominator > 0:
                            similarity = numerator / denominator
                        else:
                            similarity = 0
                
                elif isinstance(doc_vectors[0], set):
                    # 집합인 경우 (자카드 유사도)
                    v1 = doc_vectors[candidate_idx]
                    v2 = doc_vectors[selected_idx]
                    if not v1 or not v2:
                        similarity = 0
                    else:
                        similarity = len(v1 & v2) / len(v1 | v2)
                
                else:
                    try:
                        # sklearn 배열인 경우
                        from sklearn.metrics.pairwise import cosine_similarity
                        similarity = cosine_similarity(
                            doc_vectors[candidate_idx].reshape(1, -1),
                            doc_vectors[selected_idx].reshape(1, -1)
                        )[0][0]
                    except Exception as e:
                        # 마지막 대안: 문자열 직접 비교
                        text1 = doc_contents[candidate_idx]
                        text2 = doc_contents[selected_idx]
                        common_words = set(text1.lower().split()) & set(text2.lower().split())
                        all_words = set(text1.lower().split()) | set(text2.lower().split())
                        if all_words:
                            similarity = len(common_words) / len(all_words)
                        else:
                            similarity = 0
                
                max_similarity = max(max_similarity, similarity)
            
            # MMR 점수 계산: λ * 원래점수 - (1-λ) * 최대유사도
            mmr_score = diversity_threshold * original_score - (1 - diversity_threshold) * max_similarity
            
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        
        if best_idx != -1:
            selected_results.append(candidates[best_idx])
            candidates.pop(best_idx)
        else:
            break
            
    return selected_results

def get_all_items_from_collections(collection_names: list[str]) -> dict:
    results = []

    for collection_name in collection_names:
        if collection_name:
            try:
                result = get_doc(collection_name=collection_name)
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f"Error when querying the collection: {e}")
        else:
            pass

    return merge_get_results(results)


def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    results = []
    error = False

    def process_query_collection(collection_name, query_embedding):
        try:
            if collection_name:
                result = query_doc(
                    collection_name=collection_name,
                    k=k,
                    query_embedding=query_embedding,
                )
                if result is not None:
                    return result.model_dump(), None
            return None, None
        except Exception as e:
            log.exception(f"Error when querying the collection: {e}")
            return None, e

    # Generate all query embeddings (in one call)
    query_embeddings = embedding_function(queries, prefix=RAG_EMBEDDING_QUERY_PREFIX)
    log.debug(
        f"query_collection: processing {len(queries)} queries across {len(collection_names)} collections"
    )

    with ThreadPoolExecutor() as executor:
        future_results = []
        for query_embedding in query_embeddings:
            for collection_name in collection_names:
                result = executor.submit(
                    process_query_collection, collection_name, query_embedding
                )
                future_results.append(result)
        task_results = [future.result() for future in future_results]

    for result, err in task_results:
        if err is not None:
            error = True
        elif result is not None:
            results.append(result)

    if error and not results:
        log.warning("All collection queries failed. No results returned.")

    return merge_and_sort_query_results(results, k=k)


def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
    openai_key: Optional[str] = None,
) -> dict:
    results = []
    error = False
    
    api_key = openai_key or OPENAI_API_KEY
    
    try:
        # 비동기 코드를 한 번의 호출로 처리
        expanded_queries = []
        if api_key:
            # 이벤트 루프가 이미 실행 중인지 확인하고 적절히 처리
            try:
                # 현재 이벤트 루프 가져오기 시도
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 실행 중인 루프가 있으면 새 루프를 만들지 않고 future로 처리
                    future = asyncio.run_coroutine_threadsafe(
                        process_queries_async(queries, api_key), loop
                    )
                    expanded_queries = future.result(timeout=30)  # 30초 타임아웃
                else:
                    # 루프가 실행 중이 아니면 run_until_complete 사용
                    expanded_queries = loop.run_until_complete(
                        process_queries_async(queries, api_key)
                    )
            except RuntimeError:
                # 이벤트 루프가 없으면 새로 생성
                expanded_queries = asyncio.run(process_queries_async(queries, api_key))
        else:
            log.warning("OpenAI API 키가 설정되지 않았습니다. 쿼리 향상을 건너뜁니다.")
            expanded_queries = queries
            
        log.info(f"Final expanded queries: {expanded_queries}")
        
        # 각 쿼리의 결과를 모두 수집
        all_results = []
        for collection_name in collection_names:
            try:
                log.debug(
                     f"query_collection_with_hybrid_search:VECTOR_DB_CLIENT.get:collection {collection_name}"
                )
                collection_result = VECTOR_DB_CLIENT.get(collection_name=collection_name)
                for query in expanded_queries:
                    result = get_hybrid_search_results_without_reranking(
                        collection_name=collection_name,
                        collection_result=collection_result,
                        query=query,
                        embedding_function=embedding_function,
                        k=k,
                        reranking_function=reranking_function,
                        k_reranker=k_reranker,
                        r=r,
                        hybrid_bm25_weight=hybrid_bm25_weight,
                        openai_key=api_key,
                        bm25_weight=0.3,
                        vector_weight=0.7,
                    )
                    all_results.append(result)
            except Exception as e:
                log.exception(f"Error when querying the collection with hybrid_search: {e}")
                error = True

        if error and not all_results:
            raise Exception(
                "Hybrid search failed for all collections. Using Non-hybrid search as fallback."
            )
            
        # 중복 제거 및 결과 통합 (모든 쿼리 결과를 병합)
        combined_results = merge_and_deduplicate_results(all_results)
        
        # 모든 통합된 결과에 대해 한 번만 LLM 리랭킹 수행
        if api_key and combined_results and combined_results["documents"][0]:
            log.info(f"한 번에 LLM 기반 리랭킹 수행: 문서 수={len(combined_results['documents'][0])}")
            final_results = perform_llm_reranking(
                combined_results=combined_results,
                original_query=expanded_queries,  # 원본 쿼리 사용
                k=k,
                r=r,
                openai_key=api_key,
            )
            results = [final_results]
        else:
            # API 키가 없거나 결과가 없으면 통합 결과 그대로 사용
            results = [combined_results]

        if VECTOR_DB == "chroma":
            return merge_and_sort_query_results(results, k=k)
        else:
            return merge_and_sort_query_results(results, k=k)
    except Exception as e:
        raise e


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
):
    if embedding_engine == "":
        return lambda query, prefix=None, user=None: embedding_function.encode(
            query, prompt=prefix if prefix else None
        ).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        func = lambda query, prefix=None, user=None: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            prefix=prefix,
            url=url,
            key=key,
            user=user,
        )

        def generate_multiple(query, prefix, user, func):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    embeddings.extend(
                        func(
                            query[i : i + embedding_batch_size],
                            prefix=prefix,
                            user=user,
                        )
                    )
                return embeddings
            else:
                return func(query, prefix, user)

        return lambda query, prefix=None, user=None: generate_multiple(
            query, prefix, user, func
        )
    else:
        raise ValueError(f"Unknown embedding engine: {embedding_engine}")


def get_sources_from_files(
    request,
    files,
    queries,
    embedding_function,
    k,
    reranking_function,
    k_reranker,
    r,
    hybrid_bm25_weight,
    hybrid_search,
    full_context=False,
):
    log.debug(
        f"files: {files} {queries} {embedding_function} {reranking_function} {full_context}"
    )

    extracted_collections = []
    relevant_contexts = []

    for file in files:

        context = None
        if file.get("docs"):
            # BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
            context = {
                "documents": [[doc.get("content") for doc in file.get("docs")]],
                "metadatas": [[doc.get("metadata") for doc in file.get("docs")]],
            }
        elif file.get("context") == "full":
            # Manual Full Mode Toggle
            context = {
                "documents": [[file.get("file").get("data", {}).get("content")]],
                "metadatas": [[{"file_id": file.get("id"), "name": file.get("name")}]],
            }
        elif (
            file.get("type") != "web_search"
            and request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
        ):
            # BYPASS_EMBEDDING_AND_RETRIEVAL
            if file.get("type") == "collection":
                file_ids = file.get("data", {}).get("file_ids", [])

                documents = []
                metadatas = []
                for file_id in file_ids:
                    file_object = Files.get_file_by_id(file_id)

                    if file_object:
                        documents.append(file_object.data.get("content", ""))
                        metadatas.append(
                            {
                                "file_id": file_id,
                                "name": file_object.filename,
                                "source": file_object.filename,
                            }
                        )

                context = {
                    "documents": [documents],
                    "metadatas": [metadatas],
                }

            elif file.get("id"):
                file_object = Files.get_file_by_id(file.get("id"))
                if file_object:
                    context = {
                        "documents": [[file_object.data.get("content", "")]],
                        "metadatas": [
                            [
                                {
                                    "file_id": file.get("id"),
                                    "name": file_object.filename,
                                    "source": file_object.filename,
                                }
                            ]
                        ],
                    }
            elif file.get("file").get("data"):
                context = {
                    "documents": [[file.get("file").get("data", {}).get("content")]],
                    "metadatas": [
                        [file.get("file").get("data", {}).get("metadata", {})]
                    ],
                }
        else:
            collection_names = []
            if file.get("type") == "collection":
                if file.get("legacy"):
                    collection_names = file.get("collection_names", [])
                else:
                    collection_names.append(file["id"])
            elif file.get("collection_name"):
                collection_names.append(file["collection_name"])
            elif file.get("id"):
                if file.get("legacy"):
                    collection_names.append(f"{file['id']}")
                else:
                    collection_names.append(f"file-{file['id']}")

            collection_names = set(collection_names).difference(extracted_collections)
            if not collection_names:
                log.debug(f"skipping {file} as it has already been extracted")
                continue

            if full_context:
                try:
                    context = get_all_items_from_collections(collection_names)
                except Exception as e:
                    log.exception(e)

            else:
                try:
                    context = None
                    if file.get("type") == "text":
                        context = file["content"]
                    else:
                        if hybrid_search:
                            try:
                                context = query_collection_with_hybrid_search(
                                    collection_names=collection_names,
                                    queries=queries,
                                    embedding_function=embedding_function,
                                    k=k,
                                    reranking_function=reranking_function,
                                    k_reranker=k_reranker,
                                    r=r,
                                    hybrid_bm25_weight=hybrid_bm25_weight,
                                )
                            except Exception as e:
                                log.debug(
                                    "Error when using hybrid search, using"
                                    " non hybrid search as fallback."
                                )

                        if (not hybrid_search) or (context is None):
                            context = query_collection(
                                collection_names=collection_names,
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                            )
                except Exception as e:
                    log.exception(e)

            extracted_collections.extend(collection_names)

        if context:
            if "data" in file:
                del file["data"]

            relevant_contexts.append({**context, "file": file})

    sources = []
    for context in relevant_contexts:
        try:
            if "documents" in context:
                if "metadatas" in context:
                    source = {
                        "source": context["file"],
                        "document": context["documents"][0],
                        "metadata": context["metadatas"][0],
                    }
                    if "distances" in context and context["distances"]:
                        source["distances"] = context["distances"][0]

                    sources.append(source)
        except Exception as e:
            log.exception(e)

    return sources


def get_model_path(model: str, update_model: bool = False):
    # Construct huggingface_hub kwargs with local_files_only to return the snapshot path
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME")

    local_files_only = not update_model

    if OFFLINE_MODE:
        local_files_only = True

    snapshot_kwargs = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
    }

    log.debug(f"model: {model}")
    log.debug(f"snapshot_kwargs: {snapshot_kwargs}")

    # Inspiration from upstream sentence_transformers
    if (
        os.path.exists(model)
        or ("\\" in model or model.count("/") > 1)
        and local_files_only
    ):
        # If fully qualified path exists, return input, else set repo_id
        return model
    elif "/" not in model:
        # Set valid repo_id for model short-name
        model = "sentence-transformers" + "/" + model

    snapshot_kwargs["repo_id"] = model

    # Attempt to query the huggingface_hub library to determine the local path and/or to update
    try:
        model_repo_path = snapshot_download(**snapshot_kwargs)
        log.debug(f"model_repo_path: {model_repo_path}")
        return model_repo_path
    except Exception as e:
        log.exception(f"Cannot determine model snapshot path: {e}")
        return model


def generate_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str = "https://api.openai.com/v1",
    key: str = "",
    prefix: str = None,
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    try:
        log.debug(
             f"generate_openai_batch_embeddings:model {model} batch size: {len(texts)}"
         )
        json_data = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user
                    else {}
                ),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return [elem["embedding"] for elem in data["data"]]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        log.exception(f"Error generating openai batch embeddings: {e}")
        return None


def generate_ollama_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = "",
    prefix: str = None,
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    try:
        log.debug(
             f"generate_ollama_batch_embeddings:model {model} batch size: {len(texts)}"
         )
        json_data = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/api/embed",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()

        if "embeddings" in data:
            return data["embeddings"]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        log.exception(f"Error generating ollama batch embeddings: {e}")
        return None


def generate_embeddings(
    engine: str,
    model: str,
    text: Union[str, list[str]],
    prefix: Union[str, None] = None,
    **kwargs,
):
    url = kwargs.get("url", "")
    key = kwargs.get("key", "")
    user = kwargs.get("user")

    if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
        if isinstance(text, list):
            text = [f"{prefix}{text_element}" for text_element in text]
        else:
            text = f"{prefix}{text}"

    if engine == "ollama":
        if isinstance(text, list):
            embeddings = generate_ollama_batch_embeddings(
                **{
                    "model": model,
                    "texts": text,
                    "url": url,
                    "key": key,
                    "prefix": prefix,
                    "user": user,
                }
            )
        else:
            embeddings = generate_ollama_batch_embeddings(
                **{
                    "model": model,
                    "texts": [text],
                    "url": url,
                    "key": key,
                    "prefix": prefix,
                    "user": user,
                }
            )
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "openai":
        if isinstance(text, list):
            embeddings = generate_openai_batch_embeddings(
                model, text, url, key, prefix, user
            )
        else:
            embeddings = generate_openai_batch_embeddings(
                model, [text], url, key, prefix, user
            )
        return embeddings[0] if isinstance(text, str) else embeddings


import operator
from typing import Optional, Sequence

from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document


class RerankCompressor(BaseDocumentCompressor):
    embedding_function: Any
    top_n: int
    reranking_function: Any
    r_score: float

    class Config:
        extra = "forbid"
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        reranking = self.reranking_function is not None

        if reranking:
            scores = self.reranking_function.predict(
                [(query, doc.page_content) for doc in documents]
            )
        else:
            from sentence_transformers import util

            query_embedding = self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)
            document_embedding = self.embedding_function(
                [doc.page_content for doc in documents], RAG_EMBEDDING_CONTENT_PREFIX
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        docs_with_scores = list(zip(documents, scores.tolist()))
        if self.r_score:
            docs_with_scores = [
                (d, s) for d, s in docs_with_scores if s >= self.r_score
            ]

        result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
        final_results = []
        for doc, doc_score in result[: self.top_n]:
            metadata = doc.metadata
            metadata["score"] = doc_score
            doc = Document(
                page_content=doc.page_content,
                metadata=metadata,
            )
            final_results.append(doc)
        return final_results

def get_hybrid_search_results_without_reranking(
    collection_name: str,
    collection_result: GetResult,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
    openai_key: Optional[str] = None,
    bm25_weight: float = 0.3,
    vector_weight: float = 0.7,
) -> dict:
    
    api_key = openai_key or OPENAI_API_KEY
    
    try:
        
        adjusted_weights = adjust_search_weights(query, bm25_weight, vector_weight)
        log.debug(f"get_hybrid_search_results_without_reranking:doc {collection_name}")
        bm25_retriever = BM25Retriever.from_texts(
            texts=collection_result.documents[0],
            metadatas=collection_result.metadatas[0],
        )
        bm25_retriever.k = k  # BM25에서는 더 많은 결과를 가져와 다양성 확보

        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_search_retriever], 
            weights=[adjusted_weights["bm25"], adjusted_weights["vector"]]
        )
        
        # 리랭킹 없이 하이브리드 검색 결과만 반환
        results = ensemble_retriever.invoke(query)
        result = {
            "distances": [[1.0 - i * 0.01 for i in range(len(results))]],  # 임시 점수
            "documents": [[d.page_content for d in results]],
            "metadatas": [[d.metadata for d in results]],
            "query": query,  # 원본 쿼리 정보도 저장
        }
        
        return result
    except Exception as e:
        raise e

def perform_llm_reranking(
    combined_results: dict,
    original_query: list[str],
    k: int,
    r: float,
    openai_key: str,
) -> dict:
    """통합된 검색 결과에 대해 LLM 기반 리랭킹 수행"""
    try:
        # 필요한 데이터 추출
        docs = combined_results["documents"][0]
        metas = combined_results["metadatas"][0]
        
        # 최대 문서 수 제한 (LLM 컨텍스트 길이 제한)
        # k 값을 사용하되, LLM 컨텍스트 길이 제한을 고려한 안전한 최대값(20)도 함께 적용
        SAFE_MAX_DOCS = 20  # LLM 컨텍스트 길이를 고려한 안전한 최대값
        max_docs_for_reranking = min(SAFE_MAX_DOCS, k*3, len(docs))
        log.info(f"리랭킹을 위한 문서 수: {max_docs_for_reranking}개 (요청: {k}, 안전 최대값: {SAFE_MAX_DOCS})")
        selected_docs = docs[:max_docs_for_reranking]
        selected_metas = metas[:max_docs_for_reranking]
        
        # Document 객체 생성
        document_objects = []
        for i, (doc_content, meta) in enumerate(zip(selected_docs, selected_metas)):
            # 원래 인덱스를 메타데이터에 저장
            if meta is None:
                meta = {}
            meta['original_index'] = i
            document_objects.append(
                Document(
                    page_content=doc_content,
                    metadata=meta
                )
            )
        
        # 임베딩 기반 유사도 계산 없이 직접 LLM 재랭킹 수행
        # OpenAI API 호출 준비
        log.info(f"통합된 {len(document_objects)}개 문서에 대해 LLM 리랭킹 시작")
        
        # 시스템 프롬프트 설정
        system_prompt = """역할: 당신은 사용자의 질병명 또는 암 관련 정보 쿼리에 대해 검색된 문서가 KCD 코드(한국표준질병사인분류) 또는 **암등록 관련 정보(T코드, M코드, 분화도, 편측성, SEER 코드 등)**를 얼마나 정확하고 유용하게 제공하는지 판단하는 전문가입니다.
        
목표: 주어진 쿼리(질병명, 암 관련 설명 등)와 검색 결과 문서들을 분석하여, 쿼리의 의도(특정 KCD 코드 또는 암등록 정보 획득)에 가장 부합하는 문서를 관련성 높은 순서대로 번호를 나열하고 평가합니다.

평가 기준 (총 10점 만점):
 질병명/용어 정확도 및 독립성 (최대 4점)
 문서에 쿼리의 질병명 또는 핵심 용어(예: 암 부위, 조직학명)가 **정확히 일치(Exact match)**하는 형태로 명확하게 제시되는 경우 (3-4점)
 참고: 정확히 일치하는 용어와 불필요한 수식어가 있는 용어가 함께 존재 시, 정확히 일치하는 용어 자체에 대한 명확성을 기준으로 평가 (최대 3점)
 문서에 쿼리의 질병명 또는 핵심 용어가 정확히 일치하지만, 관련성이 낮거나 불필요한 다른 정보와 함께 혼재되어 명확성이 떨어지는 경우 (1-2점)
 정확한 일치 없이, 일부 유사하거나 관련된 표현만 포함된 경우 (0점)
 
KCD 코드 또는 암등록 정보의 직접적 제공 (최대 4점)
 KCD: 쿼리된 질병명에 대한 정확한 KCD 코드(들) (필요시 †/*, T/Y 코드 포함)를 명확하게 제공하는가? (0-4점)
 정확한 코드(들)를 모두 명시적으로 제공 (4점)
 일부 코드만 제공하거나, 관련 코드를 암시하지만 명확하지 않음 (1-3점)
 코드 정보 없음 (0점)
 
 암등록: 쿼리된 암 정보에 대한 **요구되는 암등록 정보(T코드, M코드, 분화도, 편측성, SEER 코드 등)**를 정확하게 제공하는가? (0-4점)
 요구되는 핵심 정보(T/M 코드 등)를 정확하고 명확하게 제공 (4점)
 일부 정보만 제공하거나, 정보가 불명확함 (1-3점)
 관련 등록 정보 없음 (0점)
 (KCD 또는 암등록 중 쿼리의 의도에 맞는 기준으로 평가)
 
최신성 및 신뢰성 (최대 1점)
 문서가 최신 KCD 버전, 최신 암등록 지침/공지 또는 신뢰할 수 있는 공식 자료(예: 통계청, 암등록본부, 관련 학회 지침)에 기반하여 작성되었는가? (0-1점)
 특히 암등록 정보는 지침 변경이 잦으므로 최신 공지/지침 반영 여부가 중요
 
정보의 구체성 및 완전성 (최대 1점)
 KCD: 필요한 경우 검표(†)/별표(*), T/Y 코드 등 관련 코드를 완전하게 제공하는가? 급성/만성 등 세부 분류가 필요할 때 구체적인 정보를 포함하는가?
 암등록: T코드, M코드 외 분화도, 편측성, SEER 코드 등 맥락상 필요한 부가 정보를 구체적으로 제공하는가?
 (쿼리 의도에 따라 필요한 정보의 구체성과 완전성을 평가, 0-1점)
 
제외 기준:
 문서가 쿼리된 질병명이나 암 자체에 대한 설명만 장황하게 늘어놓고, 정작 핵심인 KCD 코드나 암등록 세부 정보(T/M 코드 등)를 전혀 포함하지 않는 경우 관련성이 낮다고 판단하여 낮은 점수를 부여하거나 제외 고려.
 문서가 쿼리의 의도(KCD 코드 찾기, 암등록 정보 찾기)와 본질적으로 다른 내용(예: 일반적인 건강 정보, 치료 후기 등)을 주로 담고 있을 경우 제외합니다.
 
출력 형식:
결과는 다음 형식으로 제공하세요.
순위,문서번호,점수(0-10),이유
1,3,9.5,쿼리된 질병명과 정확히 일치하며 최신 지침 기반의 정확한 KCD 코드(†/* 포함)를 명확하고 완전하게 제공함.
2,1,7.0,쿼리된 암 정보와 정확히 일치하는 T/M 코드를 제공하나, 최신 지침 변경 사항 반영 여부가 불확실하고 SEER 코드 정보가 누락됨.
3,4,4.0,질병명은 일치하나 KCD 코드를 직접 제공하지 않고 질병 정의만 설명함.
4,2,2.0,유사 질병명에 대한 정보만 포함하고 있으며, 쿼리에 대한 직접적인 KCD 코드 정보 없음.
"""

        # 사용자 프롬프트 준비
        reranking_query_context = " | ".join(original_query)
        user_prompt = f"쿼리: {reranking_query_context}\n\n"
        
        # 쿼리의 주요 키워드 추출
        query_keywords = [word for q in original_query if isinstance(q, str) for word in q.lower().split() if len(word) > 2]
        
        # 문서 내용 포함
        for i, doc in enumerate(document_objects):
            # 문서 내용 전처리 (너무 길면 잘라내기)
            content = doc.page_content
            if len(content) > 500:
                content = content[:500] + "..."
                
            user_prompt += f"문서 {i+1}:\n{content}\n\n"
        
        user_prompt += "위 문서들을 쿼리와의 관련성에 따라 재평가하고 순위를 매겨주세요."
        
        try:
            # OpenAI API 호출
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                },
                json={
                    "model": "gemini-2.5-flash-preview-05-20",  # 더 가벼운 모델 사용
                    "reasoning_effort": "none",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0,  # 일관된 결과를 위해 temperature 0
                }
            )
            
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            log.debug(f"LLM 응답: {result[:200]}...")
            
            # 응답 파싱 및 재정렬
            import re
            
            reranked_docs = []
            parsed_rankings = []
            
            # 줄 단위로 분리하고 패턴 매칭
            for line in result.split('\n'):
                # 순위,문서번호,점수,이유 패턴 찾기
                match = re.match(r'(\d+)[.,]\s*(\d+)[.,]\s*(\d+\.?\d*)[.,]?(.*)', line)
                if match:
                    rank, doc_num, llm_score, reason = match.groups()
                    parsed_rankings.append({
                        'rank': int(rank),
                        'doc_num': int(doc_num),
                        'score': float(llm_score),
                        'reason': reason.strip()
                    })
            
            # 파싱 실패 시 대체 패턴 시도
            if not parsed_rankings:
                # 문서 번호만 추출 시도
                doc_nums = re.findall(r'(?:^|\D)(\d+)(?:\D|$)', result)
                if doc_nums:
                    seen = set()
                    for num in doc_nums:
                        num = int(num)
                        if 1 <= num <= len(document_objects) and num not in seen:
                            seen.add(num)
                            parsed_rankings.append({
                                'rank': len(parsed_rankings) + 1,
                                'doc_num': num,
                                'score': 10.0 - (len(parsed_rankings) * 0.5),  # 임의 점수 부여
                                'reason': "LLM이 선택한 문서"
                            })
            
            # 파싱된 결과로 문서 재정렬
            log.info(f"파싱된 LLM 평가 결과: {len(parsed_rankings)}개")
            if parsed_rankings:
                # 새 점수 계산 및 문서 재정렬
                for ranking in sorted(parsed_rankings, key=lambda x: x['rank']):
                    doc_idx = ranking['doc_num'] - 1
                    if 0 <= doc_idx < len(document_objects):
                        doc = document_objects[doc_idx]
                        
                        # 원래 순위와 LLM 순위 차이 계산
                        original_index = doc.metadata.get('original_index', 0)
                        llm_rank = ranking['rank']
                        rank_diff = abs(original_index + 1 - llm_rank)  # original_index는 0-based이므로 +1
                        
                        # 새 점수: LLM 점수를 0-1 범위로 정규화
                        base_score = min(ranking['score'] / 10.0, 1.0)
                        
                        # 순위 차이에 따른 패널티 계산
                        # 차이가 클수록 더 큰 패널티 적용 (최대 70%까지 감소)
                        penalty_factor = min(0.5, rank_diff * 0.03)  # 차이 1당 3% 감소, 최대 50%
                        
                        # 패널티 적용된 최종 점수 계산
                        adjusted_score = base_score * (1.0 - penalty_factor)
                        
                        # 로그에 점수 조정 정보 기록
                        log.debug(f"순위 차이에 따른 점수 조정: 원래순위={original_index+1}, LLM순위={llm_rank}, "
                                 f"차이={rank_diff}, 원래점수={base_score:.2f}, 패널티={penalty_factor:.2f}, "
                                 f"조정점수={adjusted_score:.2f}")
                        
                        # 메타데이터에 LLM 평가 이유 추가
                        if doc.metadata is None:
                            doc.metadata = {}
                        doc.metadata['score'] = adjusted_score
                        doc.metadata['base_score'] = base_score  # 원래 LLM 점수도 저장
                        doc.metadata['rank_penalty'] = penalty_factor  # 패널티 정보 저장
                        doc.metadata['llm_reason'] = ranking['reason']
                        doc.metadata['llm_rank'] = ranking['rank']
                        reranked_docs.append(doc)
                
                # LLM이 언급하지 않은 문서들 처리
                mentioned_indices = set(r['doc_num'] - 1 for r in parsed_rankings)
                for i, doc in enumerate(document_objects):
                    if i not in mentioned_indices:
                        # LLM이 언급하지 않은 문서는 원래 점수의 절반으로 감소시키고 맨 뒤로
                        if doc.metadata is None:
                            doc.metadata = {}
                        doc.metadata['score'] = 0.3  # 낮은 점수 부여
                        doc.metadata['llm_reason'] = "LLM이 관련성이 낮다고 판단한 문서"
                        reranked_docs.append(doc)
                
                # 결과가 k보다 적으면 원본 문서에서 추가
                if len(reranked_docs) < 5 and len(document_objects) > len(reranked_docs):
                    added_indices = set(mentioned_indices)
                    for i, doc in enumerate(document_objects):
                        if i not in added_indices and len(reranked_docs) < 5:
                            if doc.metadata is None:
                                doc.metadata = {}
                            doc.metadata['score'] = 0.2
                            doc.metadata['llm_reason'] = "추가된 문서"
                            reranked_docs.append(doc)
                
                # 전체 문서 수 기록 (로깅용)
                total_reranked_docs = len(reranked_docs)
                
                # 최종 결과를 k개로 제한 (요청된 k 값에 따라)
                if len(reranked_docs) > 5:
                    log.info(f"리랭킹된 전체 문서 {len(reranked_docs)}개 중 상위 5개만 반환합니다.")
                    reranked_docs = reranked_docs[:5]
                
                # 로깅 상세화: 각 문서에 대한 리랭킹 결과 출력 (k개로 제한된 후)
                rerank_details = []
                for i, doc in enumerate(reranked_docs):
                    # 문서 내용 짧게 요약 (첫 30자와 마지막 20자)
                    content_preview = doc.page_content[:30].replace('\n', ' ')
                    if len(doc.page_content) > 30:
                        content_preview += "..."
                    
                    # 메타데이터에서 필요한 정보 추출
                    score = doc.metadata.get("score", "N/A")
                    base_score = doc.metadata.get("base_score", score)
                    rank_penalty = doc.metadata.get("rank_penalty", 0)
                    llm_rank = doc.metadata.get("llm_rank", "N/A")
                    llm_reason = doc.metadata.get("llm_reason", "N/A")
                    original_index = doc.metadata.get("original_index", "N/A")
                    
                    # 원본 쿼리 정보 (있으면 포함)
                    # original_query = doc.metadata.get("original_query", "")
                    query_info = f" (쿼리 컨텍스트: {reranking_query_context[:30]}...)" if reranking_query_context else ""
                    
                    # 점수 조정 정보 추가
                    score_info = f"{f'{score:.2f}' if isinstance(score, float) else score}"
                    if isinstance(base_score, float) and isinstance(rank_penalty, float) and rank_penalty > 0:
                        score_info += f" (원래: {base_score:.2f}, 패널티: {rank_penalty:.2f})"
                    
                    # 문서 상세 정보 추가 (원래순위는 0부터 시작하므로 +1)
                    rerank_details.append(
                        f"\n  {i+1}. [원래순위: {original_index + 1 if isinstance(original_index, int) else original_index}, "
                        f"LLM순위: {llm_rank}, 점수: {score_info}]{query_info}\n"
                        f"     내용: {content_preview}\n"
                        f"     이유: {llm_reason[:80] + '...' if len(llm_reason) > 80 else llm_reason}"
                    )
                
                # 결과 변환
                result = {
                    "distances": [[d.metadata.get("score", 0.5) for d in reranked_docs]],
                    "documents": [[d.page_content for d in reranked_docs]],
                    "metadatas": [[d.metadata for d in reranked_docs]],
                }
                
                # 상세 로그 출력
                log.info(f"LLM 리랭킹 완료: 총 {total_reranked_docs}개 문서 중 {len(reranked_docs)}개 반환 - {''.join(rerank_details)}")
                return result
        except Exception as e:
            log.error(f"OpenAI API 호출 오류: {e}")
            # OpenAI API 오류 시 원본 결과 반환
            raise e
            
        # 모든 처리가 실패한 경우 원본 결과 반환
        return combined_results
        
    except Exception as e:
        log.error(f"LLM 리랭킹 오류: {e}")
        # 오류 발생 시 원본 결과 반환
        return combined_results

def merge_and_deduplicate_results(all_results: list[dict]) -> dict:
    """여러 쿼리의 모든 결과를 병합하고 중복 제거하면서 각 쿼리의 상위 결과 보존"""
    if not all_results:
        return {"distances": [[]], "documents": [[]], "metadatas": [[]]}
    
    # 쿼리별 결과 그룹화
    query_results = {}  # 쿼리별 결과 저장
    
    for result in all_results:
        if "documents" in result and result["documents"] and result["documents"][0]:
            docs = result["documents"][0]
            metas = result["metadatas"][0] if "metadatas" in result and result["metadatas"] else [{}] * len(docs)
            dists = result["distances"][0] if "distances" in result and result["distances"] else [0.5] * len(docs)
            query = result.get("query", "")
            
            if query not in query_results:
                query_results[query] = {
                    "docs": [],
                    "metas": [],
                    "dists": []
                }
            
            # 문서와 메타데이터, 점수 저장
            for doc, meta, dist in zip(docs, metas, dists):
                if meta:
                    meta["original_query"] = query  # 원본 쿼리 정보 저장
                query_results[query]["docs"].append(doc)
                query_results[query]["metas"].append(meta)
                query_results[query]["dists"].append(dist)
    
    # 각 쿼리별로 상위 결과 보존 (예: 상위 3개)
    TOP_K_PER_QUERY = 3  # 각 쿼리별 보존할 상위 결과 수
    preserved_docs = []  # 보존할 문서
    preserved_metas = []  # 보존할 메타데이터
    preserved_dists = []  # 보존할 점수
    preserved_hashes = set()  # 보존된 문서 해시
    
    # 1단계: 각 쿼리별 상위 결과 보존
    for query, results in query_results.items():
        # 점수 기준으로 정렬 (높은 점수 우선)
        sorted_items = sorted(zip(results["docs"], results["metas"], results["dists"]), 
                               key=lambda x: x[2], reverse=True)
        
        preserved_count = 0
        for doc, meta, dist in sorted_items:
            # 문서 해시 계산
            doc_key = doc[:200] + doc[-100:] if len(doc) > 300 else doc
            doc_hash = hashlib.sha256(doc_key.encode()).hexdigest()
            
            # 상위 K개 이내이거나, 해시가 없는 경우 보존
            if preserved_count < TOP_K_PER_QUERY or doc_hash not in preserved_hashes:
                preserved_docs.append(doc)
                preserved_metas.append(meta)
                preserved_dists.append(dist)
                preserved_hashes.add(doc_hash)
                preserved_count += 1
                
                # 상위 K개는 해시에 추가하지 않음 (다른 쿼리에서도 상위 K개면 보존)
                if preserved_count > TOP_K_PER_QUERY:
                    preserved_hashes.add(doc_hash)
    
    # 2단계: 나머지 결과 중 중복이 아닌 결과만 추가
    remaining_docs = []
    remaining_metas = []
    remaining_dists = []
    
    for query, results in query_results.items():
        for doc, meta, dist in zip(results["docs"], results["metas"], results["dists"]):
            doc_key = doc[:200] + doc[-100:] if len(doc) > 300 else doc
            doc_hash = hashlib.sha256(doc_key.encode()).hexdigest()
            
            if doc_hash not in preserved_hashes:
                remaining_docs.append(doc)
                remaining_metas.append(meta)
                remaining_dists.append(dist)
                preserved_hashes.add(doc_hash)
    
    # 최종 결과 구성
    all_docs = preserved_docs + remaining_docs
    all_metas = preserved_metas + remaining_metas
    all_dists = preserved_dists + remaining_dists
    
    # 원래 결과와 최종 결과의 개수 로깅
    original_count = sum(len(result.get("documents", [[]])[0]) for result in all_results)
    log.info(f"병합 및 중복 제거 결과: {original_count}개 -> {len(all_docs)}개 문서 (쿼리별 상위 {TOP_K_PER_QUERY}개 보존)")
    
    return {
        "distances": [all_dists],
        "documents": [all_docs],
        "metadatas": [all_metas],
    }
