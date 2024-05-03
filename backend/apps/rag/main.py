from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
import os, shutil, logging, re
import nc_py_api
import psycopg2
from pgvector.psycopg2 import register_vector
import tempfile
import requests

from pathlib import Path
from typing import List

from chromadb.utils.batch_utils import create_batches

from langchain_community.document_loaders import (
    WebBaseLoader,
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    BSHTMLLoader,
    Docx2txtLoader,
    UnstructuredEPubLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    UnstructuredXMLLoader,
    UnstructuredRSTLoader,
    UnstructuredExcelLoader,
    YoutubeLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

import validators
import urllib.parse
import socket


from pydantic import BaseModel
from typing import Optional
import mimetypes
import uuid
import json
from constants import ERROR_MESSAGES
import sentence_transformers

from apps.web.models.documents import (
    Documents,
    DocumentForm,
    DocumentResponse,
)

from apps.rag.utils import (
    get_model_path,
    get_embedding_function,
    query_doc,
    query_doc_with_hybrid_search,
    query_collection,
    query_collection_with_hybrid_search,
)

from utils.misc import (
    calculate_sha256,
    calculate_sha256_string,
    sanitize_filename,
    extract_folders_after_data_docs,
)
from utils.utils import get_current_user, get_admin_user

from config import (
    SRC_LOG_LEVELS,
    UPLOAD_DIR,
    DOCS_DIR,
    RAG_TOP_K,
    RAG_RELEVANCE_THRESHOLD,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    ENABLE_RAG_HYBRID_SEARCH,
    RAG_RERANKING_MODEL,
    PDF_EXTRACT_IMAGES,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    DEVICE_TYPE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RAG_TEMPLATE,
    POSTGRES_CONNECTION_STRING,
    NEXTCLOUD_PASSWORD,
    NEXTCLOUD_USERNAME,
    NEXTCLOUD_URL,
    HEADERS,
    NEXTCLOUD_URL,
    ENABLE_LOCAL_WEB_FETCH,
)

from constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

app = FastAPI()

app.state.TOP_K = RAG_TOP_K
app.state.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD

app.state.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH

app.state.CHUNK_SIZE = CHUNK_SIZE
app.state.CHUNK_OVERLAP = CHUNK_OVERLAP

app.state.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
app.state.RAG_TEMPLATE = RAG_TEMPLATE

app.state.OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.OPENAI_API_KEY = RAG_OPENAI_API_KEY

app.state.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES


def update_embedding_model(
    embedding_model: str,
    update_model: bool = False,
):
    if embedding_model and app.state.RAG_EMBEDDING_ENGINE == "":
        app.state.sentence_transformer_ef = sentence_transformers.SentenceTransformer(
            get_model_path(embedding_model, update_model),
            device=DEVICE_TYPE,
            trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
        )
    else:
        app.state.sentence_transformer_ef = None


def update_reranking_model(
    reranking_model: str,
    update_model: bool = False,
):
    if reranking_model:
        app.state.sentence_transformer_rf = sentence_transformers.CrossEncoder(
            get_model_path(reranking_model, update_model),
            device=DEVICE_TYPE,
            trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
        )
    else:
        app.state.sentence_transformer_rf = None


update_embedding_model(
    app.state.RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
)

update_reranking_model(
    app.state.RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
)


app.state.EMBEDDING_FUNCTION = get_embedding_function(
    app.state.RAG_EMBEDDING_ENGINE,
    app.state.RAG_EMBEDDING_MODEL,
    app.state.sentence_transformer_ef,
    app.state.OPENAI_API_KEY,
    app.state.OPENAI_API_BASE_URL,
)

origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a connection to the PostgreSQL database
conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)

class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = "test"


class UrlForm(CollectionNameForm):
    url: str


@app.get("/")
async def get_status():
    return {
        "status": True,
        "chunk_size": app.state.CHUNK_SIZE,
        "chunk_overlap": app.state.CHUNK_OVERLAP,
        "template": app.state.RAG_TEMPLATE,
        "embedding_engine": app.state.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.RAG_EMBEDDING_MODEL,
        "reranking_model": app.state.RAG_RERANKING_MODEL,
    }


@app.get("/embedding")
async def get_embedding_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": app.state.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.RAG_EMBEDDING_MODEL,
        "openai_config": {
            "url": app.state.OPENAI_API_BASE_URL,
            "key": app.state.OPENAI_API_KEY,
        },
    }


@app.get("/reranking")
async def get_reraanking_config(user=Depends(get_admin_user)):
    return {"status": True, "reranking_model": app.state.RAG_RERANKING_MODEL}


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    embedding_engine: str
    embedding_model: str


@app.post("/embedding/update")
async def update_embedding_config(
    form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating embedding model: {app.state.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        app.state.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        app.state.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if app.state.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            if form_data.openai_config != None:
                app.state.OPENAI_API_BASE_URL = form_data.openai_config.url
                app.state.OPENAI_API_KEY = form_data.openai_config.key

        update_embedding_model(app.state.RAG_EMBEDDING_MODEL, True)

        app.state.EMBEDDING_FUNCTION = get_embedding_function(
            app.state.RAG_EMBEDDING_ENGINE,
            app.state.RAG_EMBEDDING_MODEL,
            app.state.sentence_transformer_ef,
            app.state.OPENAI_API_KEY,
            app.state.OPENAI_API_BASE_URL,
        )

        return {
            "status": True,
            "embedding_engine": app.state.RAG_EMBEDDING_ENGINE,
            "embedding_model": app.state.RAG_EMBEDDING_MODEL,
            "openai_config": {
                "url": app.state.OPENAI_API_BASE_URL,
                "key": app.state.OPENAI_API_KEY,
            },
        }
    except Exception as e:
        log.exception(f"Problem updating embedding model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class RerankingModelUpdateForm(BaseModel):
    reranking_model: str


@app.post("/reranking/update")
async def update_reranking_config(
    form_data: RerankingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating reranking model: {app.state.RAG_RERANKING_MODEL} to {form_data.reranking_model}"
    )
    try:
        app.state.RAG_RERANKING_MODEL = form_data.reranking_model

        update_reranking_model(app.state.RAG_RERANKING_MODEL, True)

        return {
            "status": True,
            "reranking_model": app.state.RAG_RERANKING_MODEL,
        }
    except Exception as e:
        log.exception(f"Problem updating reranking model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@app.get("/config")
async def get_rag_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "pdf_extract_images": app.state.PDF_EXTRACT_IMAGES,
        "chunk": {
            "chunk_size": app.state.CHUNK_SIZE,
            "chunk_overlap": app.state.CHUNK_OVERLAP,
        },
    }


class ChunkParamUpdateForm(BaseModel):
    chunk_size: int
    chunk_overlap: int


class ConfigUpdateForm(BaseModel):
    pdf_extract_images: bool
    chunk: ChunkParamUpdateForm


@app.post("/config/update")
async def update_rag_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    app.state.PDF_EXTRACT_IMAGES = form_data.pdf_extract_images
    app.state.CHUNK_SIZE = form_data.chunk.chunk_size
    app.state.CHUNK_OVERLAP = form_data.chunk.chunk_overlap

    return {
        "status": True,
        "pdf_extract_images": app.state.PDF_EXTRACT_IMAGES,
        "chunk": {
            "chunk_size": app.state.CHUNK_SIZE,
            "chunk_overlap": app.state.CHUNK_OVERLAP,
        },
    }


@app.get("/template")
async def get_rag_template(user=Depends(get_current_user)):
    return {
        "status": True,
        "template": app.state.RAG_TEMPLATE,
    }


@app.get("/query/settings")
async def get_query_settings(user=Depends(get_admin_user)):
    return {
        "status": True,
        "template": app.state.RAG_TEMPLATE,
        "k": app.state.TOP_K,
        "r": app.state.RELEVANCE_THRESHOLD,
        "hybrid": app.state.ENABLE_RAG_HYBRID_SEARCH,
    }


class QuerySettingsForm(BaseModel):
    k: Optional[int] = None
    r: Optional[float] = None
    template: Optional[str] = None
    hybrid: Optional[bool] = None


@app.post("/query/settings/update")
async def update_query_settings(
    form_data: QuerySettingsForm, user=Depends(get_admin_user)
):
    app.state.RAG_TEMPLATE = form_data.template if form_data.template else RAG_TEMPLATE
    app.state.TOP_K = form_data.k if form_data.k else 4
    app.state.RELEVANCE_THRESHOLD = form_data.r if form_data.r else 0.0
    app.state.ENABLE_RAG_HYBRID_SEARCH = form_data.hybrid if form_data.hybrid else False
    return {
        "status": True,
        "template": app.state.RAG_TEMPLATE,
        "k": app.state.TOP_K,
        "r": app.state.RELEVANCE_THRESHOLD,
        "hybrid": app.state.ENABLE_RAG_HYBRID_SEARCH,
    }


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@app.post("/query/doc")
def query_doc_handler(
    form_data: QueryDocForm,
    user=Depends(get_current_user),
):
    try:
        if app.state.ENABLE_RAG_HYBRID_SEARCH:
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=form_data.r if form_data.r else app.state.RELEVANCE_THRESHOLD,
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.TOP_K,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: List[str]
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@app.post("/query/collection")
def query_collection_handler(
    form_data: QueryCollectionsForm,
    user=Depends(get_current_user),
):
    try:
        if app.state.ENABLE_RAG_HYBRID_SEARCH:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=form_data.r if form_data.r else app.state.RELEVANCE_THRESHOLD,
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.TOP_K,
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@app.post("/youtube")
def store_youtube_video(form_data: UrlForm, user=Depends(get_current_user)):
    try:
        loader = YoutubeLoader.from_youtube_url(form_data.url, add_video_info=False)
        data = loader.load()

        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.url)[:63]

        store_data_in_vector_db(data, collection_name, overwrite=True)
        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@app.post("/web")
def store_web(form_data: UrlForm, user=Depends(get_current_user)):
    # "https://www.gutenberg.org/files/1727/1727-h/1727-h.htm"
    try:
        loader = get_web_loader(form_data.url)
        data = loader.load()

        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.url)[:63]

        store_data_in_vector_db(data, collection_name, overwrite=True)
        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def get_web_loader(url: str):
    # Check if the URL is valid
    if isinstance(validators.url(url), validators.ValidationError):
        raise ValueError(ERROR_MESSAGES.INVALID_URL)
    if not ENABLE_LOCAL_WEB_FETCH:
        # Local web fetch is disabled, filter out any URLs that resolve to private IP addresses
        parsed_url = urllib.parse.urlparse(url)
        # Get IPv4 and IPv6 addresses
        ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
        # Check if any of the resolved addresses are private
        # This is technically still vulnerable to DNS rebinding attacks, as we don't control WebBaseLoader
        for ip in ipv4_addresses:
            if validators.ipv4(ip, private=True):
                raise ValueError(ERROR_MESSAGES.INVALID_URL)
        for ip in ipv6_addresses:
            if validators.ipv6(ip, private=True):
                raise ValueError(ERROR_MESSAGES.INVALID_URL)
    return WebBaseLoader(url)


def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


def store_data_in_vector_db(data, collection_name, overwrite: bool = False) -> bool:

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.CHUNK_SIZE,
        chunk_overlap=app.state.CHUNK_OVERLAP,
        add_start_index=True,
    )

    docs = text_splitter.split_documents(data)

    if len(docs) > 0:
        log.info(f"store_data_in_vector_db {docs}")
        return store_docs_in_vector_db(docs, collection_name, overwrite), None
    else:
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)


def store_text_in_vector_db(
    text, metadata, collection_name, overwrite: bool = False
) -> bool:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.CHUNK_SIZE,
        chunk_overlap=app.state.CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = text_splitter.create_documents([text], metadatas=[metadata])
    return store_docs_in_vector_db(docs, collection_name, overwrite)


def store_docs_in_vector_db(docs, collection_name, overwrite: bool = False) -> bool:
    log.info(f"store_docs_in_vector_db {docs} {collection_name}")

    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    try:
        # Establish a connection to the PostgreSQL database
        conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        cur = conn.cursor()

        # Create the pgvector extension
        # cur.execute('CREATE EXTENSION IF NOT EXISTS pgvector')
        register_vector(conn)

        # Create a new table for the collection
        if overwrite:
            # If overwrite is True, delete the existing collection
            cur.execute(f"DROP TABLE IF EXISTS {collection_name} CASCADE")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {collection_name} (
                id UUID PRIMARY KEY,
                text TEXT,
                metadata JSONB
            )
        """)
        conn.commit()

        # Insert documents into the collection table
        for doc in docs:
            doc_id = uuid.uuid1()
            cur.execute(f"""
                INSERT INTO {collection_name} (id, text, metadata)
                VALUES (%s, %s, %s)
            """, (doc_id, doc.page_content, doc.metadata))
            conn.commit()

        # Close the PostgreSQL connection
        conn.close()
        return True
    except Exception as e:
            print(f"An error occurred: {e}")
            return False


def get_loader(filename: str, file_content_type: str, file_path: str):
    file_ext = filename.split(".")[-1].lower()
    known_type = True

    known_source_ext = [
        "go",
        "py",
        "java",
        "sh",
        "bat",
        "ps1",
        "cmd",
        "js",
        "ts",
        "css",
        "cpp",
        "hpp",
        "h",
        "c",
        "cs",
        "sql",
        "log",
        "ini",
        "pl",
        "pm",
        "r",
        "dart",
        "dockerfile",
        "env",
        "php",
        "hs",
        "hsc",
        "lua",
        "nginxconf",
        "conf",
        "m",
        "mm",
        "plsql",
        "perl",
        "rb",
        "rs",
        "db2",
        "scala",
        "bash",
        "swift",
        "vue",
        "svelte",
    ]

    if file_ext == "pdf":
        loader = PyPDFLoader(file_path, extract_images=app.state.PDF_EXTRACT_IMAGES)
    elif file_ext == "csv":
        loader = CSVLoader(file_path)
    elif file_ext == "rst":
        loader = UnstructuredRSTLoader(file_path, mode="elements")
    elif file_ext == "xml":
        loader = UnstructuredXMLLoader(file_path)
    elif file_ext in ["htm", "html"]:
        loader = BSHTMLLoader(file_path, open_encoding="unicode_escape")
    elif file_ext == "md":
        loader = UnstructuredMarkdownLoader(file_path)
    elif file_content_type == "application/epub+zip":
        loader = UnstructuredEPubLoader(file_path)
    elif (
        file_content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or file_ext in ["doc", "docx"]
    ):
        loader = Docx2txtLoader(file_path)
    elif file_content_type in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ] or file_ext in ["xls", "xlsx"]:
        loader = UnstructuredExcelLoader(file_path)
    elif file_ext in known_source_ext or (
        file_content_type and file_content_type.find("text/") >= 0
    ):
        loader = TextLoader(file_path, autodetect_encoding=True)
    else:
        loader = TextLoader(file_path, autodetect_encoding=True)
        known_type = False

    return loader, known_type


@app.post("/doc")
def store_doc(
    collection_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    log.info(f"file.content_type: {file.content_type}")
    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)
        contents = file.file.read()
        
        # Create a temporary file to write the contents
        local_file_path = "test.txt"  # Set the path to your local file
        with open(local_file_path, "wb") as local_file:
            local_file.write(contents)
            local_file.close()
            
        f = open(local_file_path, "rb")
        if collection_name == None:
            collection_name = calculate_sha256(f)[:63]
        f.close()
        
        loader, known_type = get_loader(file.filename, file.content_type, local_file_path)
        data = loader.load()

        try:
            result = store_data_in_vector_db(data, collection_name)

            if result:
                return {
                    "status": True,
                    "collection_name": collection_name,
                    "filename": filename,
                    "known_type": known_type,
                }
            os.remove(local_file_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e,
            )
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pandoc not installed",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown error",
        )



class TextRAGForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


@app.post("/text")
def store_text(
    form_data: TextRAGForm,
    user=Depends(get_current_user),
):

    collection_name = form_data.collection_name
    if collection_name == None:
        collection_name = calculate_sha256_string(form_data.content)

    result = store_text_in_vector_db(
        form_data.content,
        metadata={"name": form_data.name, "created_by": user.id},
        collection_name=collection_name,
    )

    if result:
        return {"status": True, "collection_name": collection_name}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

# Initialize Nextcloud client instance
nc = nc_py_api.Nextcloud(nextcloud_url=NEXTCLOUD_URL, nc_auth_user=NEXTCLOUD_USERNAME, nc_auth_pass=NEXTCLOUD_PASSWORD)

@app.get("/scan")
def scan_docs_dir(user=Depends(get_admin_user)):
    for node in nc.files.listdir(DOCS_DIR):
        try:
            if node.is_file:
                file_path = Path(node.path)
                filename = file_path.name
                file_content_type = mimetypes.guess_type(filename)

                # Download the file from Nextcloud
                file_content = nc.files.download(node.path)

                # Calculate SHA256 hash of the file content
                collection_name = calculate_sha256(file_content)[:63]

                loader, known_type = get_loader(filename, file_content_type[0], file_content)
                data = loader.load()

                try:
                    # Store data in vector database
                    result = store_data_in_vector_db(data, collection_name)

                    if result:
                        sanitized_filename = sanitize_filename(filename)
                        doc = Documents.get_doc_by_name(sanitized_filename)

                        if doc is None:
                            doc = Documents.insert_new_doc(
                                user.id,
                                DocumentForm(
                                    **{
                                        "name": sanitized_filename,
                                        "title": filename,
                                        "collection_name": collection_name,
                                        "filename": filename,
                                        "content": (
                                            json.dumps(
                                                {
                                                    "tags": []
                                                }
                                            )
                                        )
                                    }
                                ),
                            )
                except Exception as e:
                    log.exception(e)
                    pass

        except Exception as e:
            log.exception(e)

    return {"message": "Scan completed."}

# Function to reset the PGVector database
def reset_pgvector_db(conn):
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE vector_data")  # Assuming 'vector_data' is the table storing vectors in PGVector
        conn.commit()
    conn.close()

# Function to recursively delete files and folders
def delete_files_and_folders(directory):
    for node in nc.files.listdir(directory):
        if node.is_dir:
            # Recursively delete folders
            nc.files.delete(node.user_path, recursive=True)
        else:
            # Delete files
            nc.files.delete(node.user_path)

# Route to reset the PGVector database
@app.get("/reset/db")
def reset_vector_db(user=Depends(get_admin_user)):
    reset_pgvector_db(conn)
    return {"message": "PGVector database reset successfully."}

@app.get("/reset")
def reset_application(user=Depends(get_admin_user)):
    folder = UPLOAD_DIR

    # Delete files and folders in the specified folder
    delete_files_and_folders(folder)

    try:
        # Perform other reset operations (e.g., reset PGVector database)
        reset_pgvector_db(conn)
    except Exception as e:
        return {"error": f"Failed to reset PGVector database. Reason: {e}"}

    return {"message": "Application reset successfully."}
