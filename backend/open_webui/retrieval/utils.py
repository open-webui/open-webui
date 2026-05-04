import logging
import os
from typing import Awaitable, Optional, Union

import requests
import aiohttp
import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
import time
import re

from urllib.parse import quote
from huggingface_hub import snapshot_download
from langchain_classic.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from open_webui.config import VECTOR_DB
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT


from open_webui.models.users import UserModel
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges

from open_webui.models.chats import Chats
from open_webui.models.notes import Notes
from open_webui.models.access_grants import AccessGrants
from open_webui.utils.access_control.files import has_access_to_file

from open_webui.retrieval.vector.main import GetResult
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.misc import get_message_list

from open_webui.retrieval.web.utils import get_web_loader
from open_webui.retrieval.loaders.youtube import YoutubeLoader


from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    AIOHTTP_CLIENT_SESSION_SSL,
)
from open_webui.config import (
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
)

log = logging.getLogger(__name__)


from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever


def is_youtube_url(url: str) -> bool:
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    return re.match(youtube_regex, url) is not None


def get_loader(request, url: str):
    if is_youtube_url(url):
        return YoutubeLoader(
            url,
            language=request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            proxy_url=request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
        )
    else:
        return get_web_loader(
            url,
            verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.WEB_LOADER_CONCURRENT_REQUESTS,
            trust_env=request.app.state.config.WEB_SEARCH_TRUST_ENV,
        )


def build_loader_from_config(request):
    """Build a Loader instance with the admin's configured extraction engine settings."""
    from open_webui.retrieval.loaders.main import Loader

    config = request.app.state.config
    return Loader(
        engine=config.CONTENT_EXTRACTION_ENGINE,
        DATALAB_MARKER_API_KEY=config.DATALAB_MARKER_API_KEY,
        DATALAB_MARKER_API_BASE_URL=config.DATALAB_MARKER_API_BASE_URL,
        DATALAB_MARKER_ADDITIONAL_CONFIG=config.DATALAB_MARKER_ADDITIONAL_CONFIG,
        DATALAB_MARKER_SKIP_CACHE=config.DATALAB_MARKER_SKIP_CACHE,
        DATALAB_MARKER_FORCE_OCR=config.DATALAB_MARKER_FORCE_OCR,
        DATALAB_MARKER_PAGINATE=config.DATALAB_MARKER_PAGINATE,
        DATALAB_MARKER_STRIP_EXISTING_OCR=config.DATALAB_MARKER_STRIP_EXISTING_OCR,
        DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION=config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
        DATALAB_MARKER_FORMAT_LINES=config.DATALAB_MARKER_FORMAT_LINES,
        DATALAB_MARKER_USE_LLM=config.DATALAB_MARKER_USE_LLM,
        DATALAB_MARKER_OUTPUT_FORMAT=config.DATALAB_MARKER_OUTPUT_FORMAT,
        EXTERNAL_DOCUMENT_LOADER_URL=config.EXTERNAL_DOCUMENT_LOADER_URL,
        EXTERNAL_DOCUMENT_LOADER_API_KEY=config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        TIKA_SERVER_URL=config.TIKA_SERVER_URL,
        DOCLING_SERVER_URL=config.DOCLING_SERVER_URL,
        DOCLING_API_KEY=config.DOCLING_API_KEY,
        DOCLING_PARAMS=config.DOCLING_PARAMS,
        PDF_EXTRACT_IMAGES=config.PDF_EXTRACT_IMAGES,
        PDF_LOADER_MODE=config.PDF_LOADER_MODE,
        DOCUMENT_INTELLIGENCE_ENDPOINT=config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        DOCUMENT_INTELLIGENCE_KEY=config.DOCUMENT_INTELLIGENCE_KEY,
        DOCUMENT_INTELLIGENCE_MODEL=config.DOCUMENT_INTELLIGENCE_MODEL,
        MISTRAL_OCR_API_BASE_URL=config.MISTRAL_OCR_API_BASE_URL,
        MISTRAL_OCR_API_KEY=config.MISTRAL_OCR_API_KEY,
        PADDLEOCR_VL_BASE_URL=config.PADDLEOCR_VL_BASE_URL,
        PADDLEOCR_VL_TOKEN=config.PADDLEOCR_VL_TOKEN,
        MINERU_API_MODE=config.MINERU_API_MODE,
        MINERU_API_URL=config.MINERU_API_URL,
        MINERU_API_KEY=config.MINERU_API_KEY,
        MINERU_API_TIMEOUT=config.MINERU_API_TIMEOUT,
        MINERU_PARAMS=config.MINERU_PARAMS,
    )


def _extract_text_from_binary_response(request, response: requests.Response, url: str) -> tuple[str, list]:
    """Download response body to a temp file and extract text using the Loader pipeline."""
    import mimetypes
    import tempfile
    import urllib.parse

    content_type = response.headers.get('Content-Type', '').split(';')[0].strip()

    # Derive filename from URL path, falling back to Content-Disposition or mime guess
    url_path = urllib.parse.urlparse(url).path
    filename = os.path.basename(url_path) if url_path else ''

    if not filename or '.' not in filename:
        # Try Content-Disposition header
        cd = response.headers.get('Content-Disposition', '')
        if 'filename=' in cd:
            filename = cd.split('filename=')[-1].strip('"\'')

    if not filename or '.' not in filename:
        ext = mimetypes.guess_extension(content_type) or ''
        filename = f'download{ext}'

    suffix = '.' + filename.split('.')[-1].lower() if '.' in filename else ''

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        loader = build_loader_from_config(request)
        docs = loader.load(filename, content_type, tmp_path)
        for doc in docs:
            doc.metadata['source'] = url
        content = ' '.join([doc.page_content for doc in docs])
        return content, docs
    finally:
        os.remove(tmp_path)


def _is_text_content_type(content_type: str) -> bool:
    """Return True if the content type should be handled by the web loader."""
    ct = content_type.split(';')[0].strip().lower()
    if ct.startswith('text/'):
        return True
    if any(t in ct for t in ['xml', 'json', 'javascript']):
        return True
    return not ct  # empty / missing → assume HTML


def get_content_from_url(request, url: str) -> str:
    from open_webui.retrieval.web.utils import validate_url

    # Validate URL before making any request (blocks private IPs, non-HTTP, filter list)
    validate_url(url)

    # Streamed GET to check Content-Type without downloading the body.
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
    except Exception:
        content_type = ''
        response = None

    # Text / HTML / unknown — use the configured web loader
    if response is None or _is_text_content_type(content_type):
        if response is not None:
            response.close()
        loader = get_loader(request, url)
        docs = loader.load()
        content = ' '.join([doc.page_content for doc in docs])
        return content, docs

    # Binary content (PDF, DOCX, XLSX, PPTX, etc.) — download and extract
    try:
        return _extract_text_from_binary_response(request, response, url)
    finally:
        response.close()


CHUNK_HASH_KEY = '_chunk_hash'


def _content_hash(text: str) -> str:
    """SHA-256 hash of text, used as a stable chunk identifier for RRF dedup."""
    return hashlib.sha256(text.encode()).hexdigest()


class VectorSearchRetriever(BaseRetriever):
    collection_name: Any
    embedding_function: Any
    top_k: int

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        """Get documents relevant to a query.

        Args:
            query: String to find relevant documents for.
            run_manager: The callback handler to use.

        Returns:
            List of relevant documents.
        """
        return []

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        embedding = await self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)
        result = await ASYNC_VECTOR_DB_CLIENT.search(
            collection_name=self.collection_name,
            vectors=[embedding],
            limit=self.top_k,
        )

        ids = result.ids[0]
        metadatas = result.metadatas[0]
        documents = result.documents[0]

        results = []
        for idx in range(len(ids)):
            metadata = metadatas[idx]
            metadata[CHUNK_HASH_KEY] = _content_hash(documents[idx])
            results.append(
                Document(
                    metadata=metadata,
                    page_content=documents[idx],
                )
            )
        return results


def query_doc(collection_name: str, query_embedding: list[float], k: int, user: UserModel = None):
    try:
        log.debug(f'query_doc:doc {collection_name}')
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        if result:
            log.info(f'query_doc:result {result.ids} {result.metadatas}')

        return result
    except Exception as e:
        log.exception(f'Error querying doc {collection_name} with limit {k}: {e}')
        raise e


def get_doc(collection_name: str, user: UserModel = None):
    try:
        log.debug(f'get_doc:doc {collection_name}')
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        if result:
            log.info(f'query_doc:result {result.ids} {result.metadatas}')

        return result
    except Exception as e:
        log.exception(f'Error getting doc {collection_name}: {e}')
        raise e


def get_enriched_texts(collection_result: GetResult) -> list[str]:
    enriched_texts = []
    for idx, text in enumerate(collection_result.documents[0]):
        metadata = collection_result.metadatas[0][idx]
        metadata_parts = [text]

        # Add filename (repeat twice for extra weight in BM25 scoring)
        if metadata.get('name'):
            filename = metadata['name']
            filename_tokens = filename.replace('_', ' ').replace('-', ' ').replace('.', ' ')
            metadata_parts.append(f'Filename: {filename} {filename_tokens} {filename_tokens}')

        # Add title if available
        if metadata.get('title'):
            metadata_parts.append(f'Title: {metadata["title"]}')

        # Add document section headings if available (from markdown splitter)
        if metadata.get('headings') and isinstance(metadata['headings'], list):
            headings = ' > '.join(str(h) for h in metadata['headings'])
            metadata_parts.append(f'Section: {headings}')

        # Add source URL/path if available
        if metadata.get('source'):
            metadata_parts.append(f'Source: {metadata["source"]}')

        # Add snippet for web search results
        if metadata.get('snippet'):
            metadata_parts.append(f'Snippet: {metadata["snippet"]}')

        enriched_texts.append(' '.join(metadata_parts))

    return enriched_texts


async def query_doc_with_hybrid_search(
    collection_name: str,
    collection_result: GetResult,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
    enable_enriched_texts: bool = False,
) -> dict:
    try:
        # First check if collection_result has the required attributes
        if (
            not collection_result
            or not hasattr(collection_result, 'documents')
            or not hasattr(collection_result, 'metadatas')
        ):
            log.warning(f'query_doc_with_hybrid_search:no_docs {collection_name}')
            return {'documents': [], 'metadatas': [], 'distances': []}

        # Now safely check the documents content after confirming attributes exist
        if (
            not collection_result.documents
            or len(collection_result.documents) == 0
            or not collection_result.documents[0]
        ):
            log.warning(f'query_doc_with_hybrid_search:no_docs {collection_name}')
            return {'documents': [], 'metadatas': [], 'distances': []}

        log.debug(f'query_doc_with_hybrid_search:doc {collection_name}')

        original_texts = collection_result.documents[0]
        bm25_metadatas = [
            {**meta, CHUNK_HASH_KEY: _content_hash(original_texts[idx])}
            for idx, meta in enumerate(collection_result.metadatas[0])
        ]

        bm25_texts = get_enriched_texts(collection_result) if enable_enriched_texts else original_texts

        bm25_retriever = BM25Retriever.from_texts(
            texts=bm25_texts,
            metadatas=bm25_metadatas,
        )
        bm25_retriever.k = k

        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )

        # Use CHUNK_HASH_KEY for dedup so enriched BM25 texts don't defeat RRF
        if hybrid_bm25_weight <= 0:
            ensemble_retriever = EnsembleRetriever(
                retrievers=[vector_search_retriever],
                weights=[1.0],
                id_key=CHUNK_HASH_KEY,
            )
        elif hybrid_bm25_weight >= 1:
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever],
                weights=[1.0],
                id_key=CHUNK_HASH_KEY,
            )
        else:
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, vector_search_retriever],
                weights=[hybrid_bm25_weight, 1.0 - hybrid_bm25_weight],
                id_key=CHUNK_HASH_KEY,
            )

        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k_reranker,
            reranking_function=reranking_function,
            r_score=r,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = await compression_retriever.ainvoke(query)

        distances = [d.metadata.get('score') for d in result]
        documents = [d.page_content for d in result]
        metadatas = [d.metadata for d in result]

        # retrieve only min(k, k_reranker) items, sort and cut by distance if k < k_reranker
        if k < k_reranker:
            sorted_items = sorted(zip(distances, documents, metadatas), key=lambda x: x[0], reverse=True)
            sorted_items = sorted_items[:k]

            if sorted_items:
                distances, documents, metadatas = map(list, zip(*sorted_items))
            else:
                distances, documents, metadatas = [], [], []

        result = {
            'distances': [distances],
            'documents': [documents],
            'metadatas': [metadatas],
        }

        log.info('query_doc_with_hybrid_search:result ' + f'{result["metadatas"]} {result["distances"]}')
        return result
    except Exception as e:
        log.exception(f'Error querying doc {collection_name} with hybrid search: {e}')
        raise e


def merge_get_results(get_results: list[dict]) -> dict:
    # Initialize lists to store combined data
    combined_documents = []
    combined_metadatas = []
    combined_ids = []

    for data in get_results:
        combined_documents.extend(data['documents'][0])
        combined_metadatas.extend(data['metadatas'][0])
        combined_ids.extend(data['ids'][0])

    # Create the output dictionary
    result = {
        'documents': [combined_documents],
        'metadatas': [combined_metadatas],
        'ids': [combined_ids],
    }

    return result


def merge_and_sort_query_results(query_results: list[dict], k: int) -> dict:
    # Initialize lists to store combined data
    combined = dict()  # To store documents with unique document hashes

    for data in query_results:
        if (
            len(data.get('distances', [])) == 0
            or len(data.get('documents', [])) == 0
            or len(data.get('metadatas', [])) == 0
        ):
            continue

        distances = data['distances'][0]
        documents = data['documents'][0]
        metadatas = data['metadatas'][0]

        for distance, document, metadata in zip(distances, documents, metadatas):
            if isinstance(document, str):
                doc_hash = hashlib.sha256(document.encode()).hexdigest()  # Compute a hash for uniqueness

                if doc_hash not in combined.keys():
                    combined[doc_hash] = (distance, document, metadata)
                    continue  # if doc is new, no further comparison is needed

                # if doc is alredy in, but new distance is better, update
                if distance > combined[doc_hash][0]:
                    combined[doc_hash] = (distance, document, metadata)

    combined = list(combined.values())
    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=True)

    # Slice to keep only the top k elements
    sorted_distances, sorted_documents, sorted_metadatas = zip(*combined[:k]) if combined else ([], [], [])

    # Create and return the output dictionary
    return {
        'distances': [list(sorted_distances)],
        'documents': [list(sorted_documents)],
        'metadatas': [list(sorted_metadatas)],
    }


def get_all_items_from_collections(collection_names: list[str]) -> dict:
    results = []

    for collection_name in collection_names:
        if collection_name:
            try:
                result = get_doc(collection_name=collection_name)
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f'Error when querying the collection: {e}')
        else:
            pass

    return merge_get_results(results)


async def query_collection(
    request,
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    # When request is provided, try hybrid search + reranking if enabled
    if request and request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
        try:
            reranking_function = (
                (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents))
                if request.app.state.RERANKING_FUNCTION
                else None
            )
            return await query_collection_with_hybrid_search(
                collection_names=collection_names,
                queries=queries,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                k_reranker=request.app.state.config.TOP_K_RERANKER,
                r=request.app.state.config.RELEVANCE_THRESHOLD,
                hybrid_bm25_weight=request.app.state.config.HYBRID_BM25_WEIGHT,
                enable_enriched_texts=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS,
            )
        except Exception as e:
            log.debug(f'Hybrid search failed, falling back to vector search: {e}')

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
            log.exception(f'Error when querying the collection: {e}')
            return None, e

    # Sanitize: filter out None/empty queries to prevent embedding crashes
    # (e.g. when get_last_user_message returns None)
    queries = [q for q in queries if q]
    if not queries:
        log.warning('query_collection: all queries were None or empty, returning empty results')
        return {'distances': [[]], 'documents': [[]], 'metadatas': [[]]}

    # Generate all query embeddings (in one call)
    query_embeddings = await embedding_function(queries, prefix=RAG_EMBEDDING_QUERY_PREFIX)
    log.debug(f'query_collection: processing {len(queries)} queries across {len(collection_names)} collections')

    with ThreadPoolExecutor() as executor:
        future_results = []
        for query_embedding in query_embeddings:
            for collection_name in collection_names:
                result = executor.submit(process_query_collection, collection_name, query_embedding)
                future_results.append(result)
        task_results = [future.result() for future in future_results]

    for result, err in task_results:
        if err is not None:
            error = True
        elif result is not None:
            results.append(result)

    if error and not results:
        log.warning('All collection queries failed. No results returned.')

    return merge_and_sort_query_results(results, k=k)


async def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
    enable_enriched_texts: bool = False,
) -> dict:
    results = []
    error = False
    # Fetch every collection's contents once up front so the
    # per-query/per-document loop below can reuse them. Each fetch
    # offloads to a worker thread, so run them concurrently with
    # `asyncio.gather` instead of awaiting them serially — otherwise
    # latency scales linearly with `len(collection_names)`.
    log.debug(
        'query_collection_with_hybrid_search: prefetching %d collections',
        len(collection_names),
    )

    async def _fetch_collection(name: str):
        try:
            return name, await ASYNC_VECTOR_DB_CLIENT.get(collection_name=name)
        except Exception as e:
            log.exception(f'Failed to fetch collection {name}: {e}')
            return name, None

    collection_results = dict(await asyncio.gather(*(_fetch_collection(name) for name in collection_names)))

    log.info(f'Starting hybrid search for {len(queries)} queries in {len(collection_names)} collections...')

    async def process_query(collection_name, query):
        try:
            result = await query_doc_with_hybrid_search(
                collection_name=collection_name,
                collection_result=collection_results[collection_name],
                query=query,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                k_reranker=k_reranker,
                r=r,
                hybrid_bm25_weight=hybrid_bm25_weight,
                enable_enriched_texts=enable_enriched_texts,
            )
            return result, None
        except Exception as e:
            log.exception(f'Error when querying the collection with hybrid_search: {e}')
            return None, e

    # Prepare tasks for all collections and queries
    # Avoid running any tasks for collections that failed to fetch data (have assigned None)
    tasks = [
        (collection_name, query)
        for collection_name in collection_names
        if collection_results[collection_name] is not None
        for query in queries
    ]

    # Run all queries in parallel using asyncio.gather
    task_results = await asyncio.gather(*[process_query(collection_name, query) for collection_name, query in tasks])

    for result, err in task_results:
        if err is not None:
            error = True
        elif result is not None:
            results.append(result)

    if error and not results:
        raise Exception('Hybrid search failed for all collections. Using Non-hybrid search as fallback.')

    return merge_and_sort_query_results(results, k=k)


def generate_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str = 'https://api.openai.com/v1',
    key: str = '',
    prefix: str = None,
    user: UserModel = None,
) -> list[list[float]]:
    log.debug(f'generate_openai_batch_embeddings:model {model} batch size: {len(texts)}')
    json_data = {'input': texts, 'model': model}
    if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
        json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    }
    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)

    r = requests.post(
        f'{url}/embeddings',
        headers=headers,
        json=json_data,
    )
    r.raise_for_status()
    data = r.json()
    if 'data' in data:
        return [elem['embedding'] for elem in data['data']]
    else:
        raise ValueError("Unexpected OpenAI embeddings response: missing 'data' key")


async def agenerate_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str = 'https://api.openai.com/v1',
    key: str = '',
    prefix: str = None,
    user: UserModel = None,
) -> list[list[float]]:
    log.debug(f'agenerate_openai_batch_embeddings:model {model} batch size: {len(texts)}')
    form_data = {'input': texts, 'model': model}
    if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
        form_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    }
    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)

    async with aiohttp.ClientSession(
        trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    ) as session:
        async with session.post(
            f'{url}/embeddings',
            headers=headers,
            json=form_data,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            r.raise_for_status()
            data = await r.json()
            if 'data' in data:
                return [item['embedding'] for item in data['data']]
            else:
                raise ValueError("Unexpected OpenAI embeddings response: missing 'data' key")


def generate_azure_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = '',
    version: str = '',
    prefix: str = None,
    user: UserModel = None,
) -> list[list[float]]:
    log.debug(f'generate_azure_openai_batch_embeddings:deployment {model} batch size: {len(texts)}')
    json_data = {'input': texts}
    if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
        json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

    url = f'{url}/openai/deployments/{model}/embeddings?api-version={version}'

    for _ in range(5):
        headers = {
            'Content-Type': 'application/json',
            'api-key': key,
        }
        if ENABLE_FORWARD_USER_INFO_HEADERS and user:
            headers = include_user_info_headers(headers, user)

        r = requests.post(
            url,
            headers=headers,
            json=json_data,
        )
        if r.status_code == 429:
            retry = float(r.headers.get('Retry-After', '1'))
            time.sleep(retry)
            continue
        r.raise_for_status()
        data = r.json()
        if 'data' in data:
            return [elem['embedding'] for elem in data['data']]
        else:
            raise ValueError("Unexpected Azure OpenAI embeddings response: missing 'data' key")
    raise Exception('Azure OpenAI embedding request failed: max retries (429) exceeded')


async def agenerate_azure_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = '',
    version: str = '',
    prefix: str = None,
    user: UserModel = None,
) -> list[list[float]]:
    log.debug(f'agenerate_azure_openai_batch_embeddings:deployment {model} batch size: {len(texts)}')
    form_data = {'input': texts}
    if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
        form_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

    full_url = f'{url}/openai/deployments/{model}/embeddings?api-version={version}'

    headers = {
        'Content-Type': 'application/json',
        'api-key': key,
    }
    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)

    async with aiohttp.ClientSession(
        trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    ) as session:
        async with session.post(
            full_url,
            headers=headers,
            json=form_data,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            r.raise_for_status()
            data = await r.json()
            if 'data' in data:
                return [item['embedding'] for item in data['data']]
            else:
                raise ValueError("Unexpected Azure OpenAI embeddings response: missing 'data' key")


def generate_ollama_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = '',
    prefix: str = None,
    user: UserModel = None,
) -> list[list[float]]:
    log.debug(f'generate_ollama_batch_embeddings:model {model} batch size: {len(texts)}')
    json_data = {'input': texts, 'model': model, 'truncate': True}
    if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
        json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    }
    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)

    r = requests.post(
        f'{url}/api/embed',
        headers=headers,
        json=json_data,
    )
    if r.status_code != 200:
        error_detail = r.json().get('error', r.text)
        raise Exception(f'Ollama embed error ({r.status_code}): {error_detail}')
    data = r.json()

    if 'embeddings' in data:
        return data['embeddings']
    else:
        raise ValueError("Unexpected Ollama embeddings response: missing 'embeddings' key")


async def agenerate_ollama_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = '',
    prefix: str = None,
    user: UserModel = None,
) -> list[list[float]]:
    log.debug(f'agenerate_ollama_batch_embeddings:model {model} batch size: {len(texts)}')
    form_data = {'input': texts, 'model': model, 'truncate': True}
    if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
        form_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    }
    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)

    async with aiohttp.ClientSession(
        trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    ) as session:
        async with session.post(
            f'{url}/api/embed',
            headers=headers,
            json=form_data,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            if r.status != 200:
                error_data = await r.json()
                error_detail = error_data.get('error', str(error_data))
                raise Exception(f'Ollama embed error ({r.status}): {error_detail}')
            data = await r.json()
            if 'embeddings' in data:
                return data['embeddings']
            else:
                raise ValueError("Unexpected Ollama embeddings response: missing 'embeddings' key")


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
    azure_api_version=None,
    enable_async=True,
    concurrent_requests=0,
) -> Awaitable:
    if embedding_engine == '':
        # Sentence transformers: CPU-bound sync operation
        async def async_embedding_function(query, prefix=None, user=None):
            return await asyncio.to_thread(
                (
                    lambda query, prefix=None: embedding_function.encode(
                        query,
                        batch_size=int(embedding_batch_size),
                        **({'prompt': prefix} if prefix else {}),
                    ).tolist()
                ),
                query,
                prefix,
            )

        return async_embedding_function
    elif embedding_engine in ['ollama', 'openai', 'azure_openai']:
        embedding_function = lambda query, prefix=None, user=None: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            prefix=prefix,
            url=url,
            key=key,
            user=user,
            azure_api_version=azure_api_version,
        )

        async def async_embedding_function(query, prefix=None, user=None):
            if isinstance(query, list):
                # Create batches
                batches = [query[i : i + embedding_batch_size] for i in range(0, len(query), embedding_batch_size)]

                if enable_async:
                    log.debug(f'generate_multiple_async: Processing {len(batches)} batches in parallel')
                    # Use semaphore to limit concurrent embedding API requests
                    # 0 = unlimited (no semaphore)
                    if concurrent_requests:
                        semaphore = asyncio.Semaphore(concurrent_requests)

                        async def generate_batch_with_semaphore(batch):
                            async with semaphore:
                                return await embedding_function(batch, prefix=prefix, user=user)

                        tasks = [generate_batch_with_semaphore(batch) for batch in batches]
                    else:
                        tasks = [embedding_function(batch, prefix=prefix, user=user) for batch in batches]
                    batch_results = await asyncio.gather(*tasks)
                else:
                    log.debug(f'generate_multiple_async: Processing {len(batches)} batches sequentially')
                    batch_results = []
                    for batch in batches:
                        batch_results.append(await embedding_function(batch, prefix=prefix, user=user))

                # Flatten results — raise if any batch failed
                embeddings = []
                for i, batch_embeddings in enumerate(batch_results):
                    if batch_embeddings is None:
                        raise Exception(f'Embedding generation failed for batch {i + 1}/{len(batches)}')
                    embeddings.extend(batch_embeddings)

                log.debug(
                    f'generate_multiple_async: Generated {len(embeddings)} embeddings from {len(batches)} parallel batches'
                )
                return embeddings
            else:
                return await embedding_function(query, prefix, user)

        return async_embedding_function
    else:
        raise ValueError(f'Unknown embedding engine: {embedding_engine}')


async def generate_embeddings(
    engine: str,
    model: str,
    text: Union[str, list[str]],
    prefix: Union[str, None] = None,
    **kwargs,
):
    url = kwargs.get('url', '')
    key = kwargs.get('key', '')
    user = kwargs.get('user')

    if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
        if isinstance(text, list):
            text = [f'{prefix}{text_element}' for text_element in text]
        else:
            text = f'{prefix}{text}'

    if engine == 'ollama':
        embeddings = await agenerate_ollama_batch_embeddings(
            **{
                'model': model,
                'texts': text if isinstance(text, list) else [text],
                'url': url,
                'key': key,
                'prefix': prefix,
                'user': user,
            }
        )
        if embeddings is None:
            return None
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == 'openai':
        embeddings = await agenerate_openai_batch_embeddings(
            model, text if isinstance(text, list) else [text], url, key, prefix, user
        )
        if embeddings is None:
            return None
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == 'azure_openai':
        azure_api_version = kwargs.get('azure_api_version', '')
        embeddings = await agenerate_azure_openai_batch_embeddings(
            model,
            text if isinstance(text, list) else [text],
            url,
            key,
            azure_api_version,
            prefix,
            user,
        )
        if embeddings is None:
            return None
        return embeddings[0] if isinstance(text, str) else embeddings


def get_reranking_function(reranking_engine, reranking_model, reranking_function, reranking_batch_size=32):
    if reranking_function is None:
        return None
    if reranking_engine == 'external':
        return lambda query, documents, user=None: reranking_function.predict(
            [(query, doc.page_content) for doc in documents], user=user
        )
    else:
        return lambda query, documents, user=None: reranking_function.predict(
            [(query, doc.page_content) for doc in documents], batch_size=int(reranking_batch_size)
        )


async def filter_accessible_collections(
    collection_names: set[str],
    user: UserModel,
    access_type: str = 'read',
) -> set[str]:
    """
    Return only the collection names the user is allowed to access.
    Admins bypass all checks.  For non-admins the policy is:

      - file-*          → validated via has_access_to_file
      - user-memory-*   → must match user's own memory collection
      - web-search-*    → ephemeral per-query collections, always allowed
      - knowledge-bases → always denied (system meta-collection)
      - everything else → if the name matches a knowledge base, validated
                          via Knowledges.check_access_by_user_id; if no
                          such KB exists, the name is treated as an
                          ephemeral/legacy collection and allowed
    """
    if user.role == 'admin':
        return collection_names

    validated = set()
    for name in collection_names:
        if name == 'knowledge-bases':
            # System meta-collection — never exposed to non-admins.
            continue
        elif name.startswith('file-'):
            file_id = name[len('file-') :]
            if await has_access_to_file(file_id=file_id, access_type=access_type, user=user):
                validated.add(name)
        elif name.startswith('user-memory-'):
            if name == f'user-memory-{user.id}':
                validated.add(name)
        elif name.startswith('web-search-'):
            # Ephemeral collections created by process_web_search — safe
            # to allow because they contain only transient web-search
            # results scoped to the requesting user's session.
            validated.add(name)
        else:
            # May be a knowledge-base ID or a legacy/ephemeral collection.
            # If it IS a KB, enforce access control.  If no such KB
            # exists, treat it as a non-sensitive collection (e.g. legacy
            # model knowledge, process_text SHA256 collections) and allow.
            if await Knowledges.check_access_by_user_id(name, user.id, permission=access_type):
                validated.add(name)
            elif not await Knowledges.get_knowledge_by_id(name):
                # Not a KB at all — legacy/ephemeral collection, allow
                validated.add(name)
    return validated


async def get_sources_from_items(
    request,
    items,
    queries,
    embedding_function,
    k,
    reranking_function,
    k_reranker,
    r,
    hybrid_bm25_weight,
    hybrid_search,
    full_context=False,
    user: Optional[UserModel] = None,
):
    log.debug(f'items: {items} {queries} {embedding_function} {reranking_function} {full_context}')

    extracted_collections = []
    query_results = []

    for item in items:
        query_result = None
        collection_names = []

        if item.get('type') == 'text':
            # Raw Text
            # Used during temporary chat file uploads or web page & youtube attachements

            if item.get('context') == 'full':
                if item.get('file'):
                    # if item has file data, use it
                    query_result = {
                        'documents': [[item.get('file', {}).get('data', {}).get('content')]],
                        'metadatas': [[item.get('file', {}).get('meta', {})]],
                    }

            if query_result is None:
                # Fallback
                if item.get('collection_name'):
                    # If item has a collection name, use it
                    collection_names.append(item.get('collection_name'))
                elif item.get('file'):
                    # If item has file data, use it
                    query_result = {
                        'documents': [[item.get('file', {}).get('data', {}).get('content')]],
                        'metadatas': [[item.get('file', {}).get('meta', {})]],
                    }
                else:
                    # Fallback to item content
                    query_result = {
                        'documents': [[item.get('content')]],
                        'metadatas': [[{'file_id': item.get('id'), 'name': item.get('name')}]],
                    }

        elif item.get('type') == 'note':
            # Note Attached
            note = await Notes.get_note_by_id(item.get('id'))

            if note and (
                user.role == 'admin'
                or note.user_id == user.id
                or await AccessGrants.has_access(
                    user_id=user.id,
                    resource_type='note',
                    resource_id=note.id,
                    permission='read',
                )
            ):
                # User has access to the note
                query_result = {
                    'documents': [[note.data.get('content', {}).get('md', '')]],
                    'metadatas': [[{'file_id': note.id, 'name': note.title}]],
                }

        elif item.get('type') == 'chat':
            # Chat Attached
            chat = await Chats.get_chat_by_id(item.get('id'))

            if chat and (user.role == 'admin' or chat.user_id == user.id):
                messages_map = chat.chat.get('history', {}).get('messages', {})
                message_id = chat.chat.get('history', {}).get('currentId')

                if messages_map and message_id:
                    # Reconstruct the message list in order
                    message_list = get_message_list(messages_map, message_id)
                    message_history = '\n'.join(
                        [f'#### {m.get("role", "user").capitalize()}\n{m.get("content")}\n' for m in message_list]
                    )

                    # User has access to the chat
                    query_result = {
                        'documents': [[message_history]],
                        'metadatas': [[{'file_id': chat.id, 'name': chat.title}]],
                    }

        elif item.get('type') == 'url':
            content, docs = get_content_from_url(request, item.get('url'))
            if docs:
                query_result = {
                    'documents': [[content]],
                    'metadatas': [[{'url': item.get('url'), 'name': item.get('url')}]],
                }
        elif item.get('type') == 'file':
            if item.get('context') == 'full' or request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
                if item.get('file', {}).get('data', {}).get('content', ''):
                    # Manual Full Mode Toggle
                    # Used from chat file modal, we can assume that the file content will be available from item.get("file").get("data", {}).get("content")
                    query_result = {
                        'documents': [[item.get('file', {}).get('data', {}).get('content', '')]],
                        'metadatas': [
                            [
                                {
                                    'file_id': item.get('id'),
                                    'name': item.get('name'),
                                    **item.get('file').get('data', {}).get('metadata', {}),
                                }
                            ]
                        ],
                    }
                elif item.get('id'):
                    file_object = await Files.get_file_by_id(item.get('id'))
                    if file_object and (
                        user.role == 'admin'
                        or file_object.user_id == user.id
                        or await has_access_to_file(item.get('id'), 'read', user)
                    ):
                        query_result = {
                            'documents': [[file_object.data.get('content', '')]],
                            'metadatas': [
                                [
                                    {
                                        'file_id': item.get('id'),
                                        'name': file_object.filename,
                                        'source': file_object.filename,
                                    }
                                ]
                            ],
                        }
            else:
                # Fallback to collection names
                if item.get('legacy'):
                    collection_names.append(f'{item["id"]}')
                else:
                    collection_names.append(f'file-{item["id"]}')

        elif item.get('type') == 'collection':
            # Manual Full Mode Toggle for Collection
            knowledge_base = await Knowledges.get_knowledge_by_id(item.get('id'))

            if knowledge_base and (
                user.role == 'admin'
                or knowledge_base.user_id == user.id
                or await AccessGrants.has_access(
                    user_id=user.id,
                    resource_type='knowledge',
                    resource_id=knowledge_base.id,
                    permission='read',
                )
            ):
                if item.get('context') == 'full' or request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
                    if knowledge_base and (
                        user.role == 'admin'
                        or knowledge_base.user_id == user.id
                        or await AccessGrants.has_access(
                            user_id=user.id,
                            resource_type='knowledge',
                            resource_id=knowledge_base.id,
                            permission='read',
                        )
                    ):
                        files = await Knowledges.get_files_by_id(knowledge_base.id)

                        documents = []
                        metadatas = []
                        for file in files:
                            documents.append(file.data.get('content', ''))
                            metadatas.append(
                                {
                                    'file_id': file.id,
                                    'name': file.filename,
                                    'source': file.filename,
                                }
                            )

                        query_result = {
                            'documents': [documents],
                            'metadatas': [metadatas],
                        }
                else:
                    # Fallback to collection names
                    if item.get('legacy'):
                        collection_names = item.get('collection_names', [])
                    else:
                        collection_names.append(item['id'])

        elif item.get('docs'):
            # BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
            query_result = {
                'documents': [[doc.get('content') for doc in item.get('docs')]],
                'metadatas': [[doc.get('metadata') for doc in item.get('docs')]],
            }
        elif item.get('collection_name'):
            # Direct Collection Name
            collection_names.append(item['collection_name'])
        elif item.get('collection_names'):
            # Collection Names List
            collection_names.extend(item['collection_names'])

        # If query_result is None
        # Fallback to collection names and vector search the collections
        if query_result is None and collection_names:
            collection_names = set(collection_names).difference(extracted_collections)
            if not collection_names:
                log.debug(f'skipping {item} as it has already been extracted')
                continue

            # Filter out collections the user cannot read
            if user:
                collection_names = await filter_accessible_collections(collection_names, user)
                if not collection_names:
                    log.debug(f'access denied for all collections in item {item}')
                    continue

            try:
                if full_context:
                    # Sync helper makes blocking VECTOR_DB_CLIENT calls;
                    # offload so the async caller's event loop stays free.
                    query_result = await asyncio.to_thread(get_all_items_from_collections, collection_names)
                else:
                    query_result = await query_collection(
                        request,
                        collection_names=collection_names,
                        queries=queries,
                        embedding_function=embedding_function,
                        k=k,
                    )
            except Exception as e:
                log.exception(e)

            extracted_collections.extend(collection_names)

        if query_result:
            if 'data' in item:
                del item['data']
            query_results.append({**query_result, 'file': item})

    sources = []
    for query_result in query_results:
        try:
            if 'documents' in query_result:
                if 'metadatas' in query_result:
                    source = {
                        'source': query_result['file'],
                        'document': query_result['documents'][0],
                        'metadata': query_result['metadatas'][0],
                    }
                    if 'distances' in query_result and query_result['distances']:
                        source['distances'] = query_result['distances'][0]

                    sources.append(source)
        except Exception as e:
            log.exception(e)
    return sources


def get_model_path(model: str, update_model: bool = False):
    # Construct huggingface_hub kwargs with local_files_only to return the snapshot path
    cache_dir = os.getenv('SENTENCE_TRANSFORMERS_HOME')

    local_files_only = not update_model

    if OFFLINE_MODE:
        local_files_only = True

    snapshot_kwargs = {
        'cache_dir': cache_dir,
        'local_files_only': local_files_only,
    }

    log.debug(f'model: {model}')
    log.debug(f'snapshot_kwargs: {snapshot_kwargs}')

    # Inspiration from upstream sentence_transformers
    if os.path.exists(model) or ('\\' in model or model.count('/') > 1) and local_files_only:
        # If fully qualified path exists, return input, else set repo_id
        return model
    elif '/' not in model:
        # Set valid repo_id for model short-name
        model = 'sentence-transformers' + '/' + model

    snapshot_kwargs['repo_id'] = model

    # Attempt to query the huggingface_hub library to determine the local path and/or to update
    try:
        model_repo_path = snapshot_download(**snapshot_kwargs)
        log.debug(f'model_repo_path: {model_repo_path}')
        return model_repo_path
    except Exception as e:
        log.exception(f'Cannot determine model snapshot path: {e}')
        if OFFLINE_MODE:
            raise
        return model


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
        extra = 'forbid'
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """Compress retrieved documents given the query context.

        Args:
            documents: The retrieved documents.
            query: The query context.
            callbacks: Optional callbacks to run during compression.

        Returns:
            The compressed documents.

        """
        return []

    async def acompress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        reranking = self.reranking_function is not None

        scores = None
        if reranking:
            scores = await asyncio.to_thread(self.reranking_function, query, documents)
        else:
            from sentence_transformers import util

            query_embedding = await self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)
            document_embedding = await self.embedding_function(
                [doc.page_content for doc in documents], RAG_EMBEDDING_CONTENT_PREFIX
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        if scores is not None:
            docs_with_scores = list(
                zip(
                    documents,
                    scores.tolist() if not isinstance(scores, list) else scores,
                )
            )
            if self.r_score:
                docs_with_scores = [(d, s) for d, s in docs_with_scores if s >= self.r_score]

            result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
            final_results = []
            for doc, doc_score in result[: self.top_n]:
                metadata = doc.metadata
                metadata['score'] = doc_score
                doc = Document(
                    page_content=doc.page_content,
                    metadata=metadata,
                )
                final_results.append(doc)
            return final_results
        else:
            log.warning('No valid scores found, check your reranking function. Returning original documents.')
            return documents
