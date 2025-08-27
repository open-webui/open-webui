import black
import logging
import markdown

from open_webui.models.chats import ChatTitleMessagesForm
from open_webui.config import DATA_DIR, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.responses import FileResponse
from asyncio import create_task, sleep
from json import dumps

from open_webui.routers.files import reindex_all_files
from open_webui.routers.knowledge import reindex_knowledge_files
from open_webui.routers.memories import reindex_all_memory
from open_webui.utils.misc import get_gravatar_url
from open_webui.utils.pdf_generator import PDFGenerator
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.code_interpreter import execute_code_jupyter
from open_webui.env import SRC_LOG_LEVELS
from open_webui.socket.main import REINDEX_STATE

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


@router.get("/gravatar")
async def get_gravatar(email: str, user=Depends(get_verified_user)):
    return get_gravatar_url(email)


class CodeForm(BaseModel):
    code: str


@router.post("/code/format")
async def format_code(form_data: CodeForm, user=Depends(get_admin_user)):
    try:
        formatted_code = black.format_str(form_data.code, mode=black.Mode())
        return {"code": formatted_code}
    except black.NothingChanged:
        return {"code": form_data.code}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/code/execute")
async def execute_code(
    request: Request, form_data: CodeForm, user=Depends(get_verified_user)
):
    if request.app.state.config.CODE_EXECUTION_ENGINE == "jupyter":
        output = await execute_code_jupyter(
            request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
            form_data.code,
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == "token"
                else None
            ),
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == "password"
                else None
            ),
            request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        )

        return output
    else:
        raise HTTPException(
            status_code=400,
            detail="Code execution engine not supported",
        )


class MarkdownForm(BaseModel):
    md: str


@router.post("/markdown")
async def get_html_from_markdown(
    form_data: MarkdownForm, user=Depends(get_verified_user)
):
    return {"html": markdown.markdown(form_data.md)}


class ChatForm(BaseModel):
    title: str
    messages: list[dict]


@router.post("/pdf")
async def download_chat_as_pdf(
    form_data: ChatTitleMessagesForm, user=Depends(get_verified_user)
):
    try:
        pdf_bytes = PDFGenerator(form_data).generate_chat_pdf()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment;filename=chat.pdf"},
        )
    except Exception as e:
        log.exception(f"Error generating PDF: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/db/download")
async def download_db(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    from open_webui.internal.db import engine

    if engine.name != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_NOT_SQLITE,
        )
    return FileResponse(
        engine.url.database,
        media_type="application/octet-stream",
        filename="webui.db",
    )


@router.get("/litellm/config")
async def download_litellm_config_yaml(user=Depends(get_admin_user)):
    return FileResponse(
        f"{DATA_DIR}/litellm/config.yaml",
        media_type="application/octet-stream",
        filename="config.yaml",
    )


############################
# Reindex All Data
############################


async def run_reindex_pipeline(request: Request, user):
    try:
        for key in REINDEX_STATE.keys():
            REINDEX_STATE[key]["progress"] = 0
            REINDEX_STATE[key]["status"] = "idle"

        await reindex_all_memory(request, user)
        await reindex_all_files(request, user)
        await reindex_knowledge_files(request, user)

        log.info("Reindexing everything completed successfully.")
    except Exception as e:
        log.exception("Reindexing failed")


@router.post("/reindex", response_model=bool)
async def reindex_everything(
        request: Request,
        user=Depends(get_admin_user)
    ):
    if any(state.get("status", "idle") == "running" for state in REINDEX_STATE.values()):
        log.info("Reindexing seems to be already in progress.")
        return False

    create_task(run_reindex_pipeline(request, user))
    log.info("Reindexing pipeline started in background.")
    return True


############################
# Reindex updater stream
############################


@router.get("/reindex/stream")
async def stream_progress():
    async def event_generator():
        no_progress_counter = 0
        while True:
            # Send the entire REINDEX_STATE
            yield f"data: {dumps(REINDEX_STATE)}\n\n"

            # Check if all tasks are idle (or done) to eventually end the stream
            if all(state.get("status", "idle") != "running" for state in REINDEX_STATE.values()):
                no_progress_counter += 1
                if no_progress_counter >= 3:
                    break
            else:
                no_progress_counter = 0

            await sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
