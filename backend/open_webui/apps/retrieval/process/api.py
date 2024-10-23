import logging
from typing import Optional

from fastapi import Depends, HTTPException, status, APIRouter
from langchain_community.document_loaders import YoutubeLoader
from langchain_core.documents import Document
from pydantic import BaseModel
from starlette.requests import Request

from open_webui.apps.retrieval.process.process import ProcessFileForm, save_docs_to_vector_db
from open_webui.apps.retrieval.process.process import process_file as process_file_util
from open_webui.apps.retrieval.search.search import search_web
from open_webui.apps.retrieval.web.utils import get_web_loader
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.misc import calculate_sha256_string
from open_webui.utils.utils import get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

router = APIRouter()


class ProcessTextForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class SearchForm(CollectionNameForm):
    query: str


@router.post("/web/search")
def process_web_search(request: Request, form_data: SearchForm, user=Depends(get_verified_user)):
    try:
        logging.info(
            f"trying to web search with {request.app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query}"
        )
        web_results = search_web(request.app.state, form_data.query)
    except Exception as e:
        log.exception(e)

        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    try:
        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.query)[:63]

        urls = [result.link for result in web_results]

        loader = get_web_loader(urls)
        docs = loader.load()

        save_docs_to_vector_db(docs, collection_name, request.app.state, overwrite=True)

        return {
            "status": True,
            "collection_name": collection_name,
            "filenames": urls,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/web")
def process_web(request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = get_web_loader(
            form_data.url,
            verify_ssl=request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")
        save_docs_to_vector_db(docs, collection_name, request.app.state, overwrite=True)

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/text")
def process_text(
        request: Request,
        form_data: ProcessTextForm,
        user=Depends(get_verified_user),
):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)

    docs = [
        Document(
            page_content=form_data.content,
            metadata={"name": form_data.name, "created_by": user.id},
        )
    ]
    text_content = form_data.content
    log.debug(f"text_content: {text_content}")

    result = save_docs_to_vector_db(docs, collection_name, request.app.state)

    if result:
        return {
            "status": True,
            "collection_name": collection_name,
            "content": text_content,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post("/youtube")
def process_youtube_video(request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = YoutubeLoader.from_youtube_url(
            form_data.url,
            add_video_info=True,
            language=request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            translation=request.app.state.YOUTUBE_LOADER_TRANSLATION,
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")
        save_docs_to_vector_db(docs, collection_name, request.app.state, overwrite=True)

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/file")
def process_file(
        request: Request,
        form_data: ProcessFileForm,
        user=Depends(get_verified_user),
):
    try:
        return process_file_util(request.app.state, form_data)
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
                detail=str(e),
            )
