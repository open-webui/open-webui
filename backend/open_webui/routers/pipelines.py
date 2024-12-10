from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from starlette.responses import FileResponse


from open_webui.models.chats import ChatTitleMessagesForm
from open_webui.config import DATA_DIR, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.misc import get_gravatar_url
from open_webui.utils.pdf_generator import PDFGenerator
from open_webui.utils.auth import get_admin_user

router = APIRouter()


##################################
#
# Pipelines Endpoints
#
##################################


# TODO: Refactor pipelines API endpoints below into a separate file


@app.get("/api/pipelines/list")
async def get_pipelines_list(user=Depends(get_admin_user)):
    responses = await get_openai_models_responses()

    log.debug(f"get_pipelines_list: get_openai_models_responses returned {responses}")
    urlIdxs = [
        idx
        for idx, response in enumerate(responses)
        if response is not None and "pipelines" in response
    ]

    return {
        "data": [
            {
                "url": openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx],
                "idx": urlIdx,
            }
            for urlIdx in urlIdxs
        ]
    }


@app.post("/api/pipelines/upload")
async def upload_pipeline(
    urlIdx: int = Form(...), file: UploadFile = File(...), user=Depends(get_admin_user)
):
    print("upload_pipeline", urlIdx, file.filename)
    # Check if the uploaded file is a python file
    if not (file.filename and file.filename.endswith(".py")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Python (.py) files are allowed.",
        )

    upload_folder = f"{CACHE_DIR}/pipelines"
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, file.filename)

    r = None
    try:
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}

        with open(file_path, "rb") as f:
            files = {"file": f}
            r = requests.post(f"{url}/pipelines/upload", headers=headers, files=files)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        status_code = status.HTTP_404_NOT_FOUND
        if r is not None:
            status_code = r.status_code
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )
    finally:
        # Ensure the file is deleted after the upload is completed or on failure
        if os.path.exists(file_path):
            os.remove(file_path)


class AddPipelineForm(BaseModel):
    url: str
    urlIdx: int


@app.post("/api/pipelines/add")
async def add_pipeline(form_data: AddPipelineForm, user=Depends(get_admin_user)):
    r = None
    try:
        urlIdx = form_data.urlIdx

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.post(
            f"{url}/pipelines/add", headers=headers, json={"url": form_data.url}
        )

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


class DeletePipelineForm(BaseModel):
    id: str
    urlIdx: int


@app.delete("/api/pipelines/delete")
async def delete_pipeline(form_data: DeletePipelineForm, user=Depends(get_admin_user)):
    r = None
    try:
        urlIdx = form_data.urlIdx

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.delete(
            f"{url}/pipelines/delete", headers=headers, json={"id": form_data.id}
        )

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.get("/api/pipelines")
async def get_pipelines(urlIdx: Optional[int] = None, user=Depends(get_admin_user)):
    r = None
    try:
        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/pipelines", headers=headers)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.get("/api/pipelines/{pipeline_id}/valves")
async def get_pipeline_valves(
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
):
    r = None
    try:
        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/{pipeline_id}/valves", headers=headers)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"

        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.get("/api/pipelines/{pipeline_id}/valves/spec")
async def get_pipeline_valves_spec(
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
):
    r = None
    try:
        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/{pipeline_id}/valves/spec", headers=headers)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.post("/api/pipelines/{pipeline_id}/valves/update")
async def update_pipeline_valves(
    urlIdx: Optional[int],
    pipeline_id: str,
    form_data: dict,
    user=Depends(get_admin_user),
):
    r = None
    try:
        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.post(
            f"{url}/{pipeline_id}/valves/update",
            headers=headers,
            json={**form_data},
        )

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"

        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )
