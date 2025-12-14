import logging
import os
import time
from typing import Optional, Union, Any
from urllib.parse import quote

import requests
from huggingface_hub import snapshot_download

from open_webui.env import (
    SRC_LOG_LEVELS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    DEVICE_TYPE,
    SENTENCE_TRANSFORMERS_BACKEND,
    SENTENCE_TRANSFORMERS_MODEL_KWARGS,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
)
from open_webui.config import (
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
)
from open_webui.models.users import UserModel


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def get_model_path(model: str, update_model: bool = False) -> str:
    """
    Resolve a HuggingFace/SentenceTransformers model ID to a local snapshot path.

    This is used for local embedding/reranking models when running without an
    external embeddings API.
    """
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME")

    local_files_only = not update_model
    if OFFLINE_MODE:
        local_files_only = True

    snapshot_kwargs = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
    }

    if os.path.exists(model) or (
        ("\\" in model or model.count("/") > 1) and local_files_only
    ):
        return model

    if "/" not in model:
        model = f"sentence-transformers/{model}"

    snapshot_kwargs["repo_id"] = model

    try:
        return snapshot_download(**snapshot_kwargs)
    except Exception as e:
        log.debug(f"Cannot determine model snapshot path: {e}")
        return model


def get_ef(engine: str, embedding_model: str, auto_update: bool = False):
    """
    Return a SentenceTransformer instance when using local embeddings (engine == "").
    """
    if not embedding_model or engine != "":
        return None

    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        get_model_path(embedding_model, auto_update),
        device=DEVICE_TYPE,
        trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
        backend=SENTENCE_TRANSFORMERS_BACKEND,
        model_kwargs=SENTENCE_TRANSFORMERS_MODEL_KWARGS,
    )


def get_rf(
    engine: str = "",
    reranking_model: Optional[str] = None,
    external_reranker_url: str = "",
    external_reranker_api_key: str = "",
    auto_update: bool = False,
):
    """
    Return a reranking function instance for hybrid search.

    This is retained for compatibility (e.g. memory/reranking configs) but is not
    required for PDF chat attachments.
    """
    if not reranking_model:
        return None

    if "jinaai/jina-colbert-v2" in reranking_model:
        from open_webui.retrieval.models.colbert import ColBERT

        return ColBERT(get_model_path(reranking_model, auto_update), env=None)

    if engine == "external":
        from open_webui.retrieval.models.external import ExternalReranker

        return ExternalReranker(
            url=external_reranker_url,
            api_key=external_reranker_api_key,
            model=reranking_model,
        )

    import sentence_transformers

    rf = sentence_transformers.CrossEncoder(
        get_model_path(reranking_model, auto_update),
        device=DEVICE_TYPE,
        trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
        backend=SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
        model_kwargs=SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
    )

    try:
        model_cfg = getattr(rf, "model", None)
        if model_cfg and hasattr(model_cfg, "config"):
            cfg = model_cfg.config
            if getattr(cfg, "pad_token_id", None) is None:
                eos = getattr(cfg, "eos_token_id", None)
                if eos is not None:
                    cfg.pad_token_id = eos
    except Exception:
        pass

    return rf


def _forward_user_headers(user: Optional[UserModel]) -> dict[str, str]:
    if not ENABLE_FORWARD_USER_INFO_HEADERS or not user:
        return {}

    return {
        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
        "X-OpenWebUI-User-Id": user.id,
        "X-OpenWebUI-User-Email": user.email,
        "X-OpenWebUI-User-Role": user.role,
    }


def generate_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str = "https://api.openai.com/v1",
    key: str = "",
    prefix: str | None = None,
    user: Optional[UserModel] = None,
) -> Optional[list[list[float]]]:
    try:
        json_data: dict[str, Any] = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **_forward_user_headers(user),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return [elem["embedding"] for elem in data["data"]]
        raise Exception("Embeddings response missing 'data'")
    except Exception as e:
        log.exception(f"Error generating OpenAI batch embeddings: {e}")
        return None


def generate_azure_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = "",
    version: str = "",
    prefix: str | None = None,
    user: Optional[UserModel] = None,
) -> Optional[list[list[float]]]:
    try:
        json_data: dict[str, Any] = {"input": texts}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        request_url = f"{url}/openai/deployments/{model}/embeddings?api-version={version}"

        for _ in range(5):
            r = requests.post(
                request_url,
                headers={
                    "Content-Type": "application/json",
                    "api-key": key,
                    **_forward_user_headers(user),
                },
                json=json_data,
            )
            if r.status_code == 429:
                retry = float(r.headers.get("Retry-After", "1"))
                time.sleep(retry)
                continue

            r.raise_for_status()
            data = r.json()
            if "data" in data:
                return [elem["embedding"] for elem in data["data"]]
            raise Exception("Embeddings response missing 'data'")

        return None
    except Exception as e:
        log.exception(f"Error generating Azure OpenAI batch embeddings: {e}")
        return None


def generate_ollama_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = "",
    prefix: str | None = None,
    user: Optional[UserModel] = None,
) -> Optional[list[list[float]]]:
    try:
        json_data: dict[str, Any] = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/api/embed",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **_forward_user_headers(user),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()
        if "embeddings" in data:
            return data["embeddings"]
        raise Exception("Embeddings response missing 'embeddings'")
    except Exception as e:
        log.exception(f"Error generating Ollama batch embeddings: {e}")
        return None


def generate_embeddings(
    engine: str,
    model: str,
    text: Union[str, list[str]],
    prefix: str | None = None,
    url: str = "",
    key: str = "",
    user: Optional[UserModel] = None,
    azure_api_version: str | None = None,
):
    if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
        if isinstance(text, list):
            text = [f"{prefix}{t}" for t in text]
        else:
            text = f"{prefix}{text}"

    if engine == "ollama":
        embeddings = generate_ollama_batch_embeddings(
            model=model,
            texts=text if isinstance(text, list) else [text],
            url=url,
            key=key,
            prefix=prefix,
            user=user,
        )
        return embeddings[0] if isinstance(text, str) else embeddings

    if engine == "openai":
        embeddings = generate_openai_batch_embeddings(
            model=model,
            texts=text if isinstance(text, list) else [text],
            url=url,
            key=key,
            prefix=prefix,
            user=user,
        )
        return embeddings[0] if isinstance(text, str) else embeddings

    if engine == "azure_openai":
        embeddings = generate_azure_openai_batch_embeddings(
            model=model,
            texts=text if isinstance(text, list) else [text],
            url=url,
            key=key,
            version=azure_api_version or "",
            prefix=prefix,
            user=user,
        )
        return embeddings[0] if isinstance(text, str) else embeddings

    raise ValueError(f"Unknown embedding engine: {engine}")


def get_embedding_function(
    embedding_engine: str,
    embedding_model: str,
    embedding_function,
    url: str,
    key: str,
    embedding_batch_size: int,
    azure_api_version: str | None = None,
):
    if embedding_engine == "":
        return lambda query, prefix=None, user=None: embedding_function.encode(
            query, **({"prompt": prefix} if prefix else {})
        ).tolist()

    if embedding_engine in ["ollama", "openai", "azure_openai"]:
        def _single_or_batch(query, prefix, user):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    batch_embeddings = generate_embeddings(
                        engine=embedding_engine,
                        model=embedding_model,
                        text=query[i : i + embedding_batch_size],
                        prefix=prefix,
                        url=url,
                        key=key,
                        user=user,
                        azure_api_version=azure_api_version,
                    )

                    if isinstance(batch_embeddings, list):
                        embeddings.extend(batch_embeddings)
                return embeddings

            return generate_embeddings(
                engine=embedding_engine,
                model=embedding_model,
                text=query,
                prefix=prefix,
                url=url,
                key=key,
                user=user,
                azure_api_version=azure_api_version,
            )

        return lambda query, prefix=None, user=None: _single_or_batch(query, prefix, user)

    raise ValueError(f"Unknown embedding engine: {embedding_engine}")


def get_reranking_function(reranking_engine: str, reranking_function):
    if reranking_function is None:
        return None

    if reranking_engine == "external":
        return lambda sentences, user=None: reranking_function.predict(sentences, user=user)

    return lambda sentences, user=None: reranking_function.predict(sentences)

