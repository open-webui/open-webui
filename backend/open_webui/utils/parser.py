import logging
import uuid
import json
from datetime import datetime
from typing import Optional

from enum import Enum

from fastapi import Request

from pydantic import BaseModel

import sys

import tiktoken

from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document

from open_webui.env import SRC_LOG_LEVELS
from open_webui.constants import ERROR_MESSAGES
from open_webui.retrieval.utils import get_embedding_function
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class PARSING_TYPE(Enum):
    ALL = 0
    TEXT = 1
    FILE = 2
    YOUTUBE = 3
    WEB_CONTENT = 4
    WEB_SEARCH = 5


def pre(request, **kwargs):
    '''
    called before the rest of the parser functions
    '''

    docs = kwargs.pop('docs', None)
    collection_name = kwargs.pop('collection_name', None)

    def _get_docs_info(docs: list[Document]) -> str:
        docs_info = set()

        # Trying to select relevant metadata identifying the document.
        for doc in docs:
            metadata = getattr(doc, "metadata", {})
            doc_name = metadata.get("name", "")
            if not doc_name:
                doc_name = metadata.get("title", "")
            if not doc_name:
                doc_name = metadata.get("source", "")
            if doc_name:
                docs_info.add(doc_name)

        return ", ".join(docs_info)

    log.info(
        f"save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}"
    )


class Parser:
    # class Valves(BaseModel):
    #    TEST_VALVE: str

    # Update valves/ environment variables based on your selected database
    def __init__(self):
        self.name = "Default Parser"
        self.type = PARSING_TYPE.ALL
        print("ooooooooooooooooooooooooooooooooooooooooooooooo")




    def save_docs_to_vector_db(self,
                               request: Request,
                               docs,
                               collection_name,
                               metadata: Optional[dict] = None,
                               overwrite: bool = False,
                               split: bool = True,
                               add: bool = False,
                               user=None,
                               ) -> bool:
        print("AHHHHHHHHHHHHHHHHHHHH")


        with open('output2.txt', 'w') as f:
            f.write(f'test')
            f.flush()


        pre(request, docs=docs, collection_name=collection_name)

        texts, docs = self.split(request, docs)
        metadatas = self.metadata(request, collection_name, docs, metadata)
        embeddings = self.embed(request, texts, user)

        with open('/home/daniel/output.txt', 'w') as f:
            f.write(f'm: {len(metadatas)}, t: {len(texts)}, e: {len(embeddings)}')
            f.flush()

        assert len(metadatas) == len(texts) and f"length mismatch: metadata {metadatas} vs texts {texts}"
        assert len(metadatas) == len(embeddings) and f"length mismatch: metadata {metadatas} vs embeddings {embeddings}"

        self.store(request, collection_name, texts, embeddings, metadatas, overwrite, add)

        self.post(request)

    def post(self, request, **kwargs):
        '''
        called after the rest of the parser functions
        '''
        with open('output_p.txt', 'w') as f:
            f.write(f'******************************** POST')
            f.flush()

        print("Executing my_method", flush=True)
        sys.stdout.flush()  # Extra guarantee

    def metadata(self, request, collection_name, docs, metadata):
        # Check if entries with the same hash (metadata.hash) already exist
        if metadata and "hash" in metadata:
            result = VECTOR_DB_CLIENT.query(
                collection_name=collection_name,
                filter={"hash": metadata["hash"]},
            )

            if result is not None:
                existing_doc_ids = result.ids[0]
                if existing_doc_ids:
                    log.info(f"Document with hash {metadata['hash']} already exists")
                    raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

        print()

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

    def split(self, request, docs):
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


        # METADATA NEEDS TO BE GENERATED HERE

        if len(docs) == 0:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        texts = [doc.page_content for doc in docs]
        return texts, docs

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
                log.info(
                    f"collection {collection_name} already exists, overwrite is False and add is False"
                )
                return True

        log.info(f"test")
        print(f"embeddings: {len(embeddings)}")
        print(f"metadatas: {len(metadatas)}")
        print(f"text: {len(texts)}")

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
