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

from pathlib import Path
from typing import List

from chromadb.utils import embedding_functions
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
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from pydantic import BaseModel
from typing import Optional
import mimetypes
import uuid
import json


from apps.ollama.main import generate_ollama_embeddings, GenerateEmbeddingsForm

from apps.web.models.documents import (
    Documents,
    DocumentForm,
    DocumentResponse,
)

from apps.rag.utils import (
    query_doc,
    query_embeddings_doc,
    query_collection,
    query_embeddings_collection,
    get_embedding_model_path,
    generate_openai_embeddings,
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
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    DEVICE_TYPE,
    CHROMA_CLIENT,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RAG_TEMPLATE,
)

from constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

app = FastAPI()


app.state.TOP_K = 4
app.state.CHUNK_SIZE = CHUNK_SIZE
app.state.CHUNK_OVERLAP = CHUNK_OVERLAP


app.state.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.RAG_TEMPLATE = RAG_TEMPLATE

app.state.OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.OPENAI_API_KEY = RAG_OPENAI_API_KEY

app.state.PDF_EXTRACT_IMAGES = False


app.state.sentence_transformer_ef = (
    embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=get_embedding_model_path(
            app.state.RAG_EMBEDDING_MODEL, RAG_EMBEDDING_MODEL_AUTO_UPDATE
        ),
        device=DEVICE_TYPE,
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
        "embedding_engine": app.state.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.RAG_EMBEDDING_MODEL,
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

        if app.state.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            app.state.RAG_EMBEDDING_MODEL = form_data.embedding_model
            app.state.sentence_transformer_ef = None

            if form_data.openai_config != None:
                app.state.OPENAI_API_BASE_URL = form_data.openai_config.url
                app.state.OPENAI_API_KEY = form_data.openai_config.key
        else:
            sentence_transformer_ef = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=get_embedding_model_path(
                        form_data.embedding_model, True
                    ),
                    device=DEVICE_TYPE,
                )
            )
            app.state.RAG_EMBEDDING_MODEL = form_data.embedding_model
            app.state.sentence_transformer_ef = sentence_transformer_ef

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
        if app.state.RAG_EMBEDDING_ENGINE == "":
            return query_doc(
                collection_name=form_data.collection_name,
                query=form_data.query,
                k=form_data.k if form_data.k else app.state.TOP_K,
                embedding_function=app.state.sentence_transformer_ef,
            )
        else:
            if app.state.RAG_EMBEDDING_ENGINE == "ollama":
                query_embeddings = generate_ollama_embeddings(
                    GenerateEmbeddingsForm(
                        **{
                            "model": app.state.RAG_EMBEDDING_MODEL,
                            "prompt": form_data.query,
                        }
                    )
                )
            elif app.state.RAG_EMBEDDING_ENGINE == "openai":
                query_embeddings = generate_openai_embeddings(
                    model=app.state.RAG_EMBEDDING_MODEL,
                    text=form_data.query,
                    key=app.state.OPENAI_API_KEY,
                    url=app.state.OPENAI_API_BASE_URL,
                )

            return query_embeddings_doc(
                collection_name=form_data.collection_name,
                query_embeddings=query_embeddings,
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


@app.post("/query/collection")
def query_collection_handler(
    form_data: QueryCollectionsForm,
    user=Depends(get_current_user),
):
    try:
        if app.state.RAG_EMBEDDING_ENGINE == "":
            return query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                k=form_data.k if form_data.k else app.state.TOP_K,
                embedding_function=app.state.sentence_transformer_ef,
            )
        else:

            if app.state.RAG_EMBEDDING_ENGINE == "ollama":
                query_embeddings = generate_ollama_embeddings(
                    GenerateEmbeddingsForm(
                        **{
                            "model": app.state.RAG_EMBEDDING_MODEL,
                            "prompt": form_data.query,
                        }
                    )
                )
            elif app.state.RAG_EMBEDDING_ENGINE == "openai":
                query_embeddings = generate_openai_embeddings(
                    model=app.state.RAG_EMBEDDING_MODEL,
                    text=form_data.query,
                    key=app.state.OPENAI_API_KEY,
                    url=app.state.OPENAI_API_BASE_URL,
                )

            return query_embeddings_collection(
                collection_names=form_data.collection_names,
                query_embeddings=query_embeddings,
                k=form_data.k if form_data.k else app.state.TOP_K,
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
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
        if overwrite:
            for collection in CHROMA_CLIENT.list_collections():
                if collection_name == collection.name:
                    log.info(f"deleting existing collection {collection_name}")
                    CHROMA_CLIENT.delete_collection(name=collection_name)

        if app.state.RAG_EMBEDDING_ENGINE == "":

            collection = CHROMA_CLIENT.create_collection(
                name=collection_name,
                embedding_function=app.state.sentence_transformer_ef,
            )

            for batch in create_batches(
                api=CHROMA_CLIENT,
                ids=[str(uuid.uuid1()) for _ in texts],
                metadatas=metadatas,
                documents=texts,
            ):
                collection.add(*batch)

        else:
            collection = CHROMA_CLIENT.create_collection(name=collection_name)

            if app.state.RAG_EMBEDDING_ENGINE == "ollama":
                embeddings = [
                    generate_ollama_embeddings(
                        GenerateEmbeddingsForm(
                            **{"model": app.state.RAG_EMBEDDING_MODEL, "prompt": text}
                        )
                    )
                    for text in texts
                ]
            elif app.state.RAG_EMBEDDING_ENGINE == "openai":
                embeddings = [
                    generate_openai_embeddings(
                        model=app.state.RAG_EMBEDDING_MODEL,
                        text=text,
                        key=app.state.OPENAI_API_KEY,
                        url=app.state.OPENAI_API_BASE_URL,
                    )
                    for text in texts
                ]

            for batch in create_batches(
                api=CHROMA_CLIENT,
                ids=[str(uuid.uuid1()) for _ in texts],
                metadatas=metadatas,
                embeddings=embeddings,
                documents=texts,
            ):
                collection.add(*batch)

        return True
    except Exception as e:
        log.exception(e)
        if e.__class__.__name__ == "UniqueConstraintError":
            return True

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
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        file_path = f"{UPLOAD_DIR}/{filename}"

        contents = file.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            f.close()

        f = open(file_path, "rb")
        if collection_name == None:
            collection_name = calculate_sha256(f)[:63]
        f.close()

        loader, known_type = get_loader(filename, file.content_type, file_path)
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


@app.get("/scan")
def scan_docs_dir(user=Depends(get_admin_user)):
    for path in Path(DOCS_DIR).rglob("./**/*"):
        try:
            if path.is_file() and not path.name.startswith("."):
                tags = extract_folders_after_data_docs(path)
                filename = path.name
                file_content_type = mimetypes.guess_type(path)

                f = open(path, "rb")
                collection_name = calculate_sha256(f)[:63]
                f.close()

                loader, known_type = get_loader(
                    filename, file_content_type[0], str(path)
                )
                data = loader.load()

                try:
                    result = store_data_in_vector_db(data, collection_name)

                    if result:
                        sanitized_filename = sanitize_filename(filename)
                        doc = Documents.get_doc_by_name(sanitized_filename)

                        if doc == None:
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
                                                    "tags": list(
                                                        map(
                                                            lambda name: {"name": name},
                                                            tags,
                                                        )
                                                    )
                                                }
                                            )
                                            if len(tags)
                                            else "{}"
                                        ),
                                    }
                                ),
                            )
                except Exception as e:
                    log.exception(e)
                    pass

        except Exception as e:
            log.exception(e)

    return True


@app.get("/reset/db")
def reset_vector_db(user=Depends(get_admin_user)):
    CHROMA_CLIENT.reset()


@app.get("/reset")
def reset(user=Depends(get_admin_user)) -> bool:
    folder = f"{UPLOAD_DIR}"
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            log.error("Failed to delete %s. Reason: %s" % (file_path, e))

    try:
        CHROMA_CLIENT.reset()
    except Exception as e:
        log.exception(e)

    return True
