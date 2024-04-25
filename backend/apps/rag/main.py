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
from psycopg2 import sql
import tempfile
import requests

from pathlib import Path
from typing import List

from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions

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
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from pydantic import BaseModel
from typing import Optional
import mimetypes
import uuid
import json
from constants import ERROR_MESSAGES

from apps.web.models.documents import (
    Documents,
    DocumentForm,
    DocumentResponse,
)

from apps.rag.utils import query_doc, query_collection

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
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_DEVICE_TYPE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RAG_TEMPLATE,
    POSTGRES_CONNECTION_STRING,
    NEXTCLOUD_PASSWORD,
    NEXTCLOUD_USERNAME,
    NEXTCLOUD_URL,
    HEADERS,
    NEXTCLOUD_URL,
)

from constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

#
# if RAG_EMBEDDING_MODEL:
#    sentence_transformer_ef = SentenceTransformer(
#        model_name_or_path=RAG_EMBEDDING_MODEL,
#        cache_folder=RAG_EMBEDDING_MODEL_DIR,
#        device=RAG_EMBEDDING_MODEL_DEVICE_TYPE,
#    )


app = FastAPI()

app.state.PDF_EXTRACT_IMAGES = False
app.state.CHUNK_SIZE = CHUNK_SIZE
app.state.CHUNK_OVERLAP = CHUNK_OVERLAP
app.state.RAG_TEMPLATE = RAG_TEMPLATE
app.state.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.TOP_K = 4

app.state.sentence_transformer_ef = (
    embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=app.state.RAG_EMBEDDING_MODEL,
        device=RAG_EMBEDDING_MODEL_DEVICE_TYPE,
    )
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


class StoreWebForm(CollectionNameForm):
    url: str


@app.get("/")
async def get_status():
    return {
        "status": True,
        "chunk_size": app.state.CHUNK_SIZE,
        "chunk_overlap": app.state.CHUNK_OVERLAP,
        "template": app.state.RAG_TEMPLATE,
        "embedding_model": app.state.RAG_EMBEDDING_MODEL,
    }


@app.get("/embedding/model")
async def get_embedding_model(user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_model": app.state.RAG_EMBEDDING_MODEL,
    }


class EmbeddingModelUpdateForm(BaseModel):
    embedding_model: str


@app.post("/embedding/model/update")
async def update_embedding_model(
    form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    app.state.RAG_EMBEDDING_MODEL = form_data.embedding_model
    app.state.sentence_transformer_ef = (
        embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=app.state.RAG_EMBEDDING_MODEL,
            device=RAG_EMBEDDING_MODEL_DEVICE_TYPE,
        )
    )

    return {
        "status": True,
        "embedding_model": app.state.RAG_EMBEDDING_MODEL,
    }


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
    }


class QuerySettingsForm(BaseModel):
    k: Optional[int] = None
    template: Optional[str] = None


@app.post("/query/settings/update")
async def update_query_settings(
    form_data: QuerySettingsForm, user=Depends(get_admin_user)
):
    app.state.RAG_TEMPLATE = form_data.template if form_data.template else RAG_TEMPLATE
    app.state.TOP_K = form_data.k if form_data.k else 4
    return {"status": True, "template": app.state.RAG_TEMPLATE}


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None


@app.post("/query/doc")
def query_doc_handler(
    form_data: QueryDocForm,
    user=Depends(get_current_user),
):

    try:
        return query_doc(
            collection_name=form_data.collection_name,
            query=form_data.query,
            k=form_data.k if form_data.k else app.state.TOP_K,
            embedding_function=app.state.sentence_transformer_ef,
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


@app.post("/query/collection")
def query_collection_handler(
    form_data: QueryCollectionsForm,
    user=Depends(get_current_user),
):
    return query_collection(
        collection_names=form_data.collection_names,
        query=form_data.query,
        k=form_data.k if form_data.k else app.state.TOP_K,
        embedding_function=app.state.sentence_transformer_ef,
    )


@app.post("/web")
def store_web(form_data: StoreWebForm, user=Depends(get_current_user)):
    # "https://www.gutenberg.org/files/1727/1727-h/1727-h.htm"
    try:
        loader = WebBaseLoader(form_data.url)
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


def store_data_in_vector_db(data, collection_name, overwrite: bool = False) -> bool:

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.CHUNK_SIZE,
        chunk_overlap=app.state.CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = text_splitter.split_documents(data)

    if len(docs) > 0:
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

    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    try:
        # Establish a connection to the PostgreSQL database
        conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)

        # Create a cursor to execute SQL queries
        with conn.cursor() as cursor:
            if overwrite:
                # If overwrite is True, delete the existing collection
                cursor.execute("DROP TABLE IF EXISTS %s CASCADE", (collection_name,))
                conn.commit()

            # Create a new table for the collection
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS %s (
                    id UUID PRIMARY KEY,
                    text TEXT,
                    metadata JSONB
                )
            """, (collection_name,))
            conn.commit()

            # Insert documents into the collection table
            for text, metadata in zip(texts, metadatas):
                doc_id = uuid.uuid1()
                cursor.execute("""
                    INSERT INTO %s (id, text, metadata)
                    VALUES (%s, %s, %s)
                """, (collection_name, doc_id, text, metadata))
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
    # "https://www.gutenberg.org/files/1727/1727-h/1727-h.htm"

    log.info(f"file.content_type: {file.content_type}")
    try:
        is_valid_filename = True
        unsanitized_filename = file.filename
        if re.search(r'[\\/:"\*\?<>|\n\t ]', unsanitized_filename) is not None:
            is_valid_filename = False

        unvalidated_file_path = f"{UPLOAD_DIR}/{unsanitized_filename}"
        dereferenced_file_path = str(Path(unvalidated_file_path).resolve(strict=False))
        if not dereferenced_file_path.startswith(UPLOAD_DIR):
            is_valid_filename = False

        if is_valid_filename:
            file_path = dereferenced_file_path
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )

        filename = file.filename
        contents = file.file.read()
       # Create a temporary file to write the contents
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(contents)

        # If `collection_name` is None, calculate SHA256 hash of the temporary file's contents
        if collection_name is None:
            with open(temp_file, "rb") as f:
                collection_name = calculate_sha256(f)[:63]

        loader, known_type = get_loader(file.filename, file.content_type, temp_file)
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
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
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
