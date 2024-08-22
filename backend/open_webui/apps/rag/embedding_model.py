from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from open_webui.apps.ollama.main import get_ollama_embedding_model_name_and_base_url
from open_webui.apps.rag.utils import get_model_path
from open_webui.config import (
    DEVICE_TYPE,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
)


def set_embedding_function(
    embedding_engine: Optional[str] = None,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    batch_size: Optional[int] = None,
    model_kwargs: dict = {
        "device": DEVICE_TYPE,
        "trust_remote_code": RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    },
    update_model: bool = RAG_EMBEDDING_MODEL_AUTO_UPDATE,
) -> Embeddings:
    """
    Sets embedding function with LangChain Embeddings Interface based on
    the provider (embedding_engine) with the embedding model name and other
    settings attributes.

    Args:
        embedding_engine (Optional[str]): The provider used to set the embedding function.
        model_name (Optional[str]): The embedding model name.
        base_url (Optional[str]): The base url of the server that host the
            embedding models.
        api_key (Optional[str]): The api key to call the server.
        batch_size (Optional[int]): The batch size corresponds to the number
            of texts that is handled in one batch. Only used with "openai"
            embedding engine.
        model_kwargs (dict): The settings for the embedding model. Only used when
            no embedding engine provided (local execution with SentenceTransformers).

    Returns:
        Embeddings: Returns the LangChain Embedding Interface corresponding to the
            embedding engine.
    """
    match embedding_engine:
        case "ollama":
            model_name, base_url = get_ollama_embedding_model_name_and_base_url(
                model_name
            )
            return OllamaEmbeddings(model=model_name, base_url=base_url)
        case "openai":
            return OpenAIEmbeddings(
                model=model_name,
                base_url=base_url,
                api_key=api_key,
                chunk_size=batch_size,
            )
        case _:
            model_path = get_model_path(model=model_name, update_model=update_model)
            return HuggingFaceEmbeddings(
                model_name=model_path, model_kwargs=model_kwargs
            )
