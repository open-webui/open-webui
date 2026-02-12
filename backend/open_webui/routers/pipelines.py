from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    APIRouter,
)
import aiohttp
import os
import logging
import shutil
from pydantic import BaseModel
from starlette.responses import FileResponse
from typing import Optional

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES


from open_webui.routers.openai import get_all_models_responses

from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)


##################################
#
# Pipeline Middleware
#
##################################


def get_sorted_filters(model_id, models):
    filters = [
        model
        for model in models.values()
        if "pipeline" in model
        and "type" in model["pipeline"]
        and model["pipeline"]["type"] == "filter"
        and (
            model["pipeline"]["pipelines"] == ["*"]
            or any(
                model_id == target_model_id
                for target_model_id in model["pipeline"]["pipelines"]
            )
        )
    ]
    sorted_filters = sorted(filters, key=lambda x: x["pipeline"]["priority"])
    return sorted_filters


async def process_pipeline_inlet_filter(request, payload, user, models):
    user = {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    model_id = payload["model"]
    sorted_filters = get_sorted_filters(model_id, models)
    model = models[model_id]

    if "pipeline" in model:
        sorted_filters.append(model)

    async with aiohttp.ClientSession(trust_env=True) as session:
        for filter in sorted_filters:
            urlIdx = filter.get("urlIdx")

            try:
                urlIdx = int(urlIdx)
            except:
                continue

            url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
            key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

            if not key:
                continue

            headers = {"Authorization": f"Bearer {key}"}
            request_data = {
                "user": user,
                "body": payload,
            }

            try:
                async with session.post(
                    f"{url}/{filter['id']}/filter/inlet",
                    headers=headers,
                    json=request_data,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    payload = await response.json()
                    response.raise_for_status()
            except aiohttp.ClientResponseError as e:
                res = (
                    await response.json()
                    if response.content_type == "application/json"
                    else {}
                )
                if "detail" in res:
                    raise Exception(response.status, res["detail"])
            except Exception as e:
                log.exception(f"Connection error: {e}")

    return payload


async def process_pipeline_outlet_filter(request, payload, user, models):
    user = {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    model_id = payload["model"]
    sorted_filters = get_sorted_filters(model_id, models)
    model = models[model_id]

    if "pipeline" in model:
        sorted_filters = [model] + sorted_filters

    async with aiohttp.ClientSession(trust_env=True) as session:
        for filter in sorted_filters:
            urlIdx = filter.get("urlIdx")

            try:
                urlIdx = int(urlIdx)
            except:
                continue

            url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
            key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

            if not key:
                continue

            headers = {"Authorization": f"Bearer {key}"}
            request_data = {
                "user": user,
                "body": payload,
            }

            try:
                async with session.post(
                    f"{url}/{filter['id']}/filter/outlet",
                    headers=headers,
                    json=request_data,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    payload = await response.json()
                    response.raise_for_status()
            except aiohttp.ClientResponseError as e:
                try:
                    res = (
                        await response.json()
                        if "application/json" in response.content_type
                        else {}
                    )
                    if "detail" in res:
                        raise Exception(response.status, res)
                except Exception:
                    pass
            except Exception as e:
                log.exception(f"Connection error: {e}")

    return payload


##################################
#
# Pipelines Endpoints
#
##################################

router = APIRouter()


@router.get("/list")
async def get_pipelines_list(request: Request, user=Depends(get_admin_user)):
    responses = await get_all_models_responses(request, user)
    log.debug(f"get_pipelines_list: get_openai_models_responses returned {responses}")

    urlIdxs = [
        idx
        for idx, response in enumerate(responses)
        if response is not None and "pipelines" in response
    ]

    return {
        "data": [
            {
                "url": request.app.state.config.OPENAI_API_BASE_URLS[urlIdx],
                "idx": urlIdx,
            }
            for urlIdx in urlIdxs
        ]
    }


@router.post("/upload")
async def upload_pipeline(
    request: Request,
    urlIdx: int = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_admin_user),
):
    log.info(f"upload_pipeline: urlIdx={urlIdx}, filename={file.filename}")
    filename = os.path.basename(file.filename)

    # Check if the uploaded file is a python file
    if not (filename and filename.endswith(".py")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Python (.py) files are allowed.",
        )

    upload_folder = f"{CACHE_DIR}/pipelines"
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)

    response = None
    try:
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}

        async with aiohttp.ClientSession(trust_env=True) as session:
            form_data = aiohttp.FormData()
            form_data.add_field(
                "file",
                open(file_path, "rb"),
                filename=filename,
                content_type="application/octet-stream",
            )

            async with session.post(
                f"{url}/pipelines/upload",
                headers=headers,
                data=form_data,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None
        status_code = status.HTTP_404_NOT_FOUND
        if response is not None:
            status_code = response.status
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=status_code,
            detail=detail if detail else "Pipeline not found",
        )
    finally:
        # Ensure the file is deleted after the upload is completed or on failure
        if os.path.exists(file_path):
            os.remove(file_path)


class AddPipelineForm(BaseModel):
    url: str
    urlIdx: int


@router.post("/add")
async def add_pipeline(
    request: Request, form_data: AddPipelineForm, user=Depends(get_admin_user)
):
    response = None
    try:
        urlIdx = form_data.urlIdx

        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                f"{url}/pipelines/add",
                headers={"Authorization": f"Bearer {key}"},
                json={"url": form_data.url},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None
        if response is not None:
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(
                response.status if response is not None else status.HTTP_404_NOT_FOUND
            ),
            detail=detail if detail else "Pipeline not found",
        )


class DeletePipelineForm(BaseModel):
    id: str
    urlIdx: int


@router.delete("/delete")
async def delete_pipeline(
    request: Request, form_data: DeletePipelineForm, user=Depends(get_admin_user)
):
    response = None
    try:
        urlIdx = form_data.urlIdx

        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.delete(
                f"{url}/pipelines/delete",
                headers={"Authorization": f"Bearer {key}"},
                json={"id": form_data.id},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None
        if response is not None:
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(
                response.status if response is not None else status.HTTP_404_NOT_FOUND
            ),
            detail=detail if detail else "Pipeline not found",
        )


@router.get("/")
async def get_pipelines(
    request: Request, urlIdx: Optional[int] = None, user=Depends(get_admin_user)
):
    response = None
    try:
        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                f"{url}/pipelines",
                headers={"Authorization": f"Bearer {key}"},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None
        if response is not None:
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(
                response.status if response is not None else status.HTTP_404_NOT_FOUND
            ),
            detail=detail if detail else "Pipeline not found",
        )


@router.get("/{pipeline_id}/valves")
async def get_pipeline_valves(
    request: Request,
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
):
    response = None
    try:
        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                f"{url}/{pipeline_id}/valves",
                headers={"Authorization": f"Bearer {key}"},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None
        if response is not None:
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(
                response.status if response is not None else status.HTTP_404_NOT_FOUND
            ),
            detail=detail if detail else "Pipeline not found",
        )


@router.get("/{pipeline_id}/valves/spec")
async def get_pipeline_valves_spec(
    request: Request,
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
):
    response = None
    try:
        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                f"{url}/{pipeline_id}/valves/spec",
                headers={"Authorization": f"Bearer {key}"},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None
        if response is not None:
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(
                response.status if response is not None else status.HTTP_404_NOT_FOUND
            ),
            detail=detail if detail else "Pipeline not found",
        )


@router.post("/{pipeline_id}/valves/update")
async def update_pipeline_valves(
    request: Request,
    urlIdx: Optional[int],
    pipeline_id: str,
    form_data: dict,
    user=Depends(get_admin_user),
):
    response = None
    try:
        url = request.app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = request.app.state.config.OPENAI_API_KEYS[urlIdx]

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                f"{url}/{pipeline_id}/valves/update",
                headers={"Authorization": f"Bearer {key}"},
                json={**form_data},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        log.exception(f"Connection error: {e}")

        detail = None

        if response is not None:
            try:
                res = await response.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(
                response.status if response is not None else status.HTTP_404_NOT_FOUND
            ),
            detail=detail if detail else "Pipeline not found",
        )
