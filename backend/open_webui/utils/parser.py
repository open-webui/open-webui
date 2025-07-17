import logging
import uuid
import json
from datetime import datetime
from typing import Optional, Tuple, List
from enum import Enum
from abc import ABC, abstractmethod

from fastapi import Request

import tiktoken

from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document

from open_webui.env import SRC_LOG_LEVELS
from open_webui.constants import ERROR_MESSAGES
from open_webui.retrieval.utils import get_embedding_function
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class PARSER_TYPE(Enum):  # noqa
    ALL = 0
    TEXT = 1
    FILE = 2
    YOUTUBE = 3
    WEB_CONTENT = 4
    WEB_SEARCH = 5


class ParserInterface(ABC):
    def is_applicable_to_item(self, item_id):
        print(f"item id: {item_id}")
        return True

    @abstractmethod
    def delete_doc(self, collection_name, file_id):
        assert NotImplementedError

    @abstractmethod
    def delete_collection(self, file_collection):
        assert NotImplementedError

    @abstractmethod
    def reset(self):
        assert NotImplementedError

    @abstractmethod
    def parse(self,
              request: Request,
              docs,
              metadata: Optional[dict] = None,
              user=None,
              **kwargs
              ) -> dict:
        assert NotImplementedError

    @abstractmethod
    def store(self, request, collection_name, texts, embeddings, metadatas, overwrite=False, add=True):
        assert NotImplementedError


class DefaultParser(ParserInterface):
    # Update valves/ environment variables based on your selected database
    def __init__(self, parser_type=PARSER_TYPE.ALL):
        self.name = "Default Parser"
        self.parser_type = parser_type

    def delete_doc(self, collection_name, file_id):
        try:
            VECTOR_DB_CLIENT.delete(
                collection_name=collection_name, filter={"file_id": file_id}
            )
        except Exception as e:
            print(e)

    def delete_collection(self, file_collection):
        if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection):
            VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)

    def reset(self):
        VECTOR_DB_CLIENT.reset()

    def parse(self,
              request: Request,
              docs,
              metadata: Optional[dict] = None,
              user=None,
              **kwargs
              ) -> dict:
        docs = self.split(request, docs, **kwargs)
        texts = [doc.page_content for doc in docs]
        metadatas = self.metadata(request, docs, metadata)

        assert texts is not None
        try:
            embeddings = self.embed(request, texts, user)
        except RuntimeError as e:
            print("embedding was cancelled")
            raise
        
        assert len(metadatas) == len(texts) and f"length mismatch: metadata {metadatas} vs texts {texts}"
        assert len(metadatas) == len(embeddings) and f"length mismatch: metadata {metadatas} vs embeddings {embeddings}"

        return {"texts": texts, "embeddings": embeddings, "metadatas": metadatas}

    def split(self, request, docs, **kwargs) -> Tuple[List[Document]]:
        if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        elif request.app.state.config.TEXT_SPLITTER == "token":
            log.info(
                f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
            )

            tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
            text_splitter = TokenTextSplitter(
                encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        else:
            raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))

        docs = text_splitter.split_documents(docs)

        if len(docs) == 0:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        return docs

    def metadata(self, request, docs, metadata):
        metadatas = [
            {
                **doc.metadata,
                **(metadata if metadata else {}),
                "embedding_config": json.dumps(
                    {
                        "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
                        "model": request.app.state.config.RAG_EMBEDDING_MODEL,
                    }
                ),
            }
            for doc in docs
        ]

        # ChromaDB does not like datetime formats
        # for meta-data so convert them to string.
        for metadata in metadatas:
            for key, value in metadata.items():
                if (
                        isinstance(value, datetime)
                        or isinstance(value, list)
                        or isinstance(value, dict)
                ):
                    metadata[key] = str(value)

        return metadatas

    def embed(self, request, texts, user=None):
        embedding_function = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_BASE_URL
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_API_KEY
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        embeddings = embedding_function(
            list(map(lambda x: x.replace("\n", " "), texts)), user=user
        )

        return embeddings

    def store(self, request, collection_name, texts, embeddings, metadatas, overwrite=False, add=True):
        # don't do this until the last step to limit deleting collections if errors are thrown

        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            log.info(f"collection {collection_name} already exists")

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                log.info(f"deleting existing collection {collection_name}")
            elif not add:
                print("collection {collection_name} already exists, overwrite is False and add is False")
                log.info(
                    f"collection {collection_name} already exists, overwrite is False and add is False"
                )
                return True

        items = [
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "vector": embeddings[idx],
                "metadata": metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        VECTOR_DB_CLIENT.insert(
            collection_name=collection_name,
            items=items,
        )
