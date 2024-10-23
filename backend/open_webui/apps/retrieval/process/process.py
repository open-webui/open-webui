import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, TokenTextSplitter
from pydantic import BaseModel

from open_webui.apps.retrieval.loaders.main import Loader
from open_webui.apps.retrieval.search.embeddings import get_embedding_function
from open_webui.apps.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.apps.webui.models.files import Files
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.storage.provider import Storage
from open_webui.utils.misc import calculate_sha256_string

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def save_docs_to_vector_db(
    docs,
    collection_name,
    state,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
) -> bool:
    log.info(f"save_docs_to_vector_db {docs} {collection_name}")

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

    if split:
        if state.config.TEXT_SPLITTER in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=state.config.CHUNK_SIZE,
                chunk_overlap=state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        elif state.config.TEXT_SPLITTER == "token":
            text_splitter = TokenTextSplitter(
                encoding_name=state.config.TIKTOKEN_ENCODING_NAME,
                chunk_size=state.config.CHUNK_SIZE,
                chunk_overlap=state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        else:
            raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))

        docs = text_splitter.split_documents(docs)

    if len(docs) == 0:
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    texts = [doc.page_content for doc in docs]
    metadatas = [
        {
            **doc.metadata,
            **(metadata if metadata else {}),
            "embedding_config": json.dumps(
                {
                    "engine": state.config.RAG_EMBEDDING_ENGINE,
                    "model": state.config.RAG_EMBEDDING_MODEL,
                }
            ),
        }
        for doc in docs
    ]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if isinstance(value, datetime):
                metadata[key] = str(value)

    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            log.info(f"collection {collection_name} already exists")

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                log.info(f"deleting existing collection {collection_name}")
            elif add is False:
                log.info(
                    f"collection {collection_name} already exists, overwrite is False and add is False"
                )
                return True

        log.info(f"adding to collection {collection_name}")
        embedding_function = get_embedding_function(
            state.config.RAG_EMBEDDING_ENGINE,
            state.config.RAG_EMBEDDING_MODEL,
            state.sentence_transformer_ef,
            state.config.OPENAI_API_KEY,
            state.config.OPENAI_API_BASE_URL,
            state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        embeddings = embedding_function(
            list(map(lambda x: x.replace("\n", " "), texts))
        )

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

        return True
    except Exception as e:
        log.exception(e)
        return False


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


def process_file(state, form_data: ProcessFileForm):
    file = Files.get_file_by_id(form_data.file_id)

    collection_name = form_data.collection_name

    if collection_name is None:
        collection_name = f"file-{file.id}"

    if form_data.content:
        # Update the content in the file
        # Usage: /files/{file_id}/data/content/update

        VECTOR_DB_CLIENT.delete(
            collection_name=f"file-{file.id}",
            filter={"file_id": file.id},
        )

        docs = [
            Document(
                page_content=form_data.content,
                metadata={
                    "name": file.meta.get("name", file.filename),
                    "created_by": file.user_id,
                    "file_id": file.id,
                    **file.meta,
                },
            )
        ]

        text_content = form_data.content
    elif form_data.collection_name:
        # Check if the file has already been processed and save the content
        # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

        result = VECTOR_DB_CLIENT.query(
            collection_name=f"file-{file.id}", filter={"file_id": file.id}
        )

        if result is not None and len(result.ids[0]) > 0:
            docs = [
                Document(
                    page_content=result.documents[0][idx],
                    metadata=result.metadatas[0][idx],
                )
                for idx, id in enumerate(result.ids[0])
            ]
        else:
            docs = [
                Document(
                    page_content=file.data.get("content", ""),
                    metadata={
                        "name": file.meta.get("name", file.filename),
                        "created_by": file.user_id,
                        "file_id": file.id,
                        **file.meta,
                    },
                )
            ]

        text_content = file.data.get("content", "")
    else:
        # Process the file and save the content
        # Usage: /files/
        file_path = file.path
        if file_path:
            file_path = Storage.get_file(file_path)
            loader = Loader(
                engine=state.config.CONTENT_EXTRACTION_ENGINE,
                TIKA_SERVER_URL=state.config.TIKA_SERVER_URL,
                PDF_EXTRACT_IMAGES=state.config.PDF_EXTRACT_IMAGES,
            )
            docs = loader.load(file.filename, file.meta.get("content_type"), file_path)
        else:
            docs = [
                Document(
                    page_content=file.data.get("content", ""),
                    metadata={
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        **file.meta,
                    },
                )
            ]
        text_content = " ".join([doc.page_content for doc in docs])

    log.debug(f"text_content: {text_content}")
    Files.update_file_data_by_id(
        file.id,
        {"content": text_content},
    )

    hash = calculate_sha256_string(text_content)
    Files.update_file_hash_by_id(file.id, hash)

    try:
        result = save_docs_to_vector_db(
            docs=docs,
            collection_name=collection_name,
            state=state,
            metadata={
                "file_id": file.id,
                "name": file.meta.get("name", file.filename),
                "hash": hash,
            },
            add=(True if form_data.collection_name else False),
        )

        if result:
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "collection_name": collection_name,
                },
            )

            return {
                "status": True,
                "collection_name": collection_name,
                "filename": file.meta.get("name", file.filename),
                "content": text_content,
            }
    except Exception as e:
        raise e
