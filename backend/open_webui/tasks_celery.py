# tasks.py
import json
import logging
from uuid import uuid4

from datetime import datetime
from langchain_core.documents import Document
from open_webui.celery_worker import celery_app


from open_webui.storage.provider import Storage
# Document loaders
from open_webui.retrieval.loaders.main import Loader
from open_webui.models.files import Files
from open_webui.routers.retrieval import is_valid_pdf
from open_webui.exceptions import InvalidPDFError
from open_webui.routers.retrieval import get_ef
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.config import VECTOR_DB
from typing import Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
import tiktoken
from open_webui.env import (
    SRC_LOG_LEVELS,
)

from open_webui.retrieval.utils import (
    get_embedding_function,
)

from open_webui.utils.misc import (
    calculate_sha256_string,
)

from open_webui.constants import ERROR_MESSAGES
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


@celery_app.task
def process_tasks(args):
    """Executa OCR e processamento do PDF de forma assíncrona."""
    try:
        content = process_file_celery(args)

        return {"status": "completed", "result": content, "cd_hash": args["task_id"]}
    except Exception as e:
        log.exception("Erro na tarefa em background")
        return {"status": "failed", "error": str(e), "cd_hash": args["task_id"]}


def process_file_celery(args):
    try:
        file = Files.get_file_by_id(args["task_id"])

        engine = args["engine"]
        is_pdf2text = (
            engine == "pdftotext" and file.meta.get(
                "content_type") == "application/pdf"
        )

        if args["collection_name"] is None:
            args["collection_name"] = f"file-{file.id}"

        # Process the file and save the content
        # Usage: /files/
        file_path = file.path
        text_content = ""
        if file_path:
            file_path = Storage.get_file(file_path)
            file_ext = file.filename.split(".")[-1].lower()
            if file_ext == "pdf":
                try:
                    is_valid_pdf(file_path)
                except InvalidPDFError as e:
                    log.exception(f"Erro na tarefa em background: {e}")
                    raise e
            file_path = Storage.get_file(file_path)
            loader = Loader(
                engine=engine,
                TIKA_SERVER_URL=args["tika_server_url"],
                PDFTOTEXT_SERVER_URL=args["pdftotext_server_url"],
                PDF_EXTRACT_IMAGES=args["pdf_extract_images"],
                MAXPAGES_PDFTOTEXT=args["maxpages_pdftotext"],
            )
            if is_pdf2text:
                task_id = loader.load(
                    file.filename,
                    file.meta.get("content_type"),
                    file_path,
                    is_async=True,
                )

                text_content = loader.loader.get_text(task_id)

                docs = [
                    Document(
                        page_content=text_content,
                        metadata={
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                ]

                log.info(f"OCR Task {task_id} created successfully.")

            else:
                docs = loader.load(
                    file.filename, file.meta.get("content_type"), file_path
                )
                docs = [
                    Document(
                        page_content=doc.page_content,
                        metadata={
                            **doc.metadata,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                    for doc in docs
                ]
        else:
            docs = [
                Document(
                    page_content=file.data.get("content", ""),
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

        if not is_pdf2text:
            text_content = " ".join([doc.page_content for doc in docs])

        Files.update_file_data_by_id(
            file.id,
            {"content": text_content},
        )

        hash = calculate_sha256_string(text_content)
        Files.update_file_hash_by_id(file.id, hash)

        try:
            result = save_docs_to_vector_db_celery(
                docs=docs,
                metadata={
                    "file_id": file.id,
                    "name": file.filename,
                    "hash": hash,
                },
                add=(True if args["collection_name"] else False),
                args=args,
            )

            if result:
                Files.update_file_metadata_by_id(
                    file.id,
                    {
                        "collection_name": args["collection_name"],
                    },
                )

                return {
                    "status": True,
                    "collection_name": args["collection_name"],
                    "filename": file.filename,
                    "content": text_content,
                }
        except Exception as e:
            raise e

    except Exception as e:
        log.exception(e)
        raise e


def save_docs_to_vector_db_celery(
    docs,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
    args: dict = {},
) -> bool:
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
        f"save_docs_to_vector_db: document {_get_docs_info(docs)} {args['collection_name']}"
    )

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and "hash" in metadata:
        result = VECTOR_DB_CLIENT.query(
            collection_name=args["collection_name"],
            filter={"hash": metadata["hash"]},
        )

        if result is not None:
            existing_doc_ids = result.ids[0]
            if existing_doc_ids:
                log.info(
                    f"Document with hash {metadata['hash']} already exists")
                raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        if args["text_splitter"] in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=args["chunk_size"],
                chunk_overlap=args["chunk_overlap"],
                add_start_index=True,
            )
        elif args["text_splitter"] == "token":
            log.info(
                f"Using token text splitter: {args['tiktoken_encoding_name']}"
            )

            tiktoken.get_encoding(
                str(args["tiktoken_encoding_name"]))
            text_splitter = TokenTextSplitter(
                encoding_name=str(
                    args["tiktoken_encoding_name"]),
                chunk_size=args["chunk_size"],
                chunk_overlap=args["chunk_overlap"],
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
                    "engine": args["rag_embedding_engine"],
                    "model": args["rag_embedding_model"],
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

    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=args["collection_name"]):
            log.info(f"collection {args['collection_name']} already exists")

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(
                    collection_name=args["collection_name"])
                log.info(
                    f"deleting existing collection {args['collection_name']}")
            elif add is False:
                log.info(
                    f"collection {args['collection_name']} already exists, overwrite is False and add is False"
                )
                return True

        log.info(f"adding to collection {args['collection_name']}")

        if VECTOR_DB != 'weaviate':
            ef = get_ef(
                args["rag_embedding_engine"],
                args["rag_embedding_model"],
            )
            embedding_function = get_embedding_function(
                args["rag_embedding_engine"],
                args["rag_embedding_model"],
                ef,
                (
                    args["rag_openai_base_url"]
                    if args["rag_embedding_engine"] == "openai"
                    else args["rag_ollama_base_url"]
                ),
                (
                    args["rag_openai_api_key"]
                    if args["rag_embedding_engine"] == "openai"
                    else args["rag_ollama_api_key"]
                ),
                args["rag_embedding_batch_size"],
            )

            embeddings = embedding_function(
                list(map(lambda x: x.replace("\n", " "), texts))
            )

            items = [
                {
                    "id": str(uuid4()),
                    "text": text,
                    "vector": embeddings[idx],
                    "metadata": metadatas[idx],
                }
                for idx, text in enumerate(texts)
            ]
        else:
            items = [
                {
                    "id": str(uuid4()),
                    "text": text,
                    "metadata": metadatas[idx],
                }
                for idx, text in enumerate(texts)
            ]

        VECTOR_DB_CLIENT.insert(
            collection_name=args["collection_name"],
            items=items,
        )

        return True
    except Exception as e:
        log.exception(e)
        raise e
