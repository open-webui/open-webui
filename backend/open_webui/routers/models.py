from typing import Optional
import io
import base64
import json
import asyncio
import logging

from open_webui.models.groups import Groups
from open_webui.models.models import (
    ModelForm,
    ModelModel,
    ModelResponse,
    ModelListResponse,
    ModelAccessListResponse,
    ModelAccessResponse,
    Models,
)

from pydantic import BaseModel
from open_webui.constants import ERROR_MESSAGES
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
    Response,
)
from fastapi.responses import FileResponse, StreamingResponse


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL, STATIC_DIR
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()


def is_valid_model_id(model_id: str) -> bool:
    return model_id and len(model_id) <= 256


###########################
# GetModels
###########################


PAGE_ITEM_COUNT = 30


@router.get(
    "/list", response_model=ModelAccessListResponse
)  # do NOT use "/" as path, conflicts with main.py
async def get_models(
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    tag: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if view_option:
        filter["view_option"] = view_option
    if tag:
        filter["tag"] = tag
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    if not user.role == "admin" or not BYPASS_ADMIN_ACCESS_CONTROL:
        groups = Groups.get_groups_by_member_id(user.id, db=db)
        if groups:
            filter["group_ids"] = [group.id for group in groups]

        filter["user_id"] = user.id

    result = Models.search_models(user.id, filter=filter, skip=skip, limit=limit, db=db)
    return ModelAccessListResponse(
        items=[
            ModelAccessResponse(
                **model.model_dump(),
                write_access=(
                    (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == model.user_id
                    or has_access(user.id, "write", model.access_control, db=db)
                ),
            )
            for model in result.items
        ],
        total=result.total,
    )


###########################
# GetBaseModels
###########################


@router.get("/base", response_model=list[ModelResponse])
async def get_base_models(
    user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    return Models.get_base_models(db=db)


###########################
# GetModelTags
###########################


@router.get("/tags", response_model=list[str])
async def get_model_tags(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        models = Models.get_models(db=db)
    else:
        models = Models.get_models_by_user_id(user.id, db=db)

    tags_set = set()
    for model in models:
        if model.meta:
            meta = model.meta.model_dump()
            for tag in meta.get("tags", []):
                tags_set.add((tag.get("name")))

    tags = [tag for tag in tags_set]
    tags.sort()
    return tags


############################
# CreateNewModel
############################


@router.post("/create", response_model=Optional[ModelModel])
async def create_new_model(
    request: Request,
    form_data: ModelForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.models", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    model = Models.get_model_by_id(form_data.id, db=db)
    if model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.MODEL_ID_TAKEN,
        )

    if not is_valid_model_id(form_data.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.MODEL_ID_TOO_LONG,
        )

    else:
        model = Models.insert_new_model(form_data, user.id, db=db)
        if model:
            return model
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.DEFAULT(),
            )


############################
# ExportModels
############################


@router.get("/export", response_model=list[ModelModel])
async def export_models(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id,
        "workspace.models_export",
        request.app.state.config.USER_PERMISSIONS,
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        return Models.get_models(db=db)
    else:
        return Models.get_models_by_user_id(user.id, db=db)


############################
# ImportModels
############################


class ModelsImportForm(BaseModel):
    models: list[dict]


@router.post("/import", response_model=bool)
async def import_models(
    request: Request,
    user=Depends(get_verified_user),
    form_data: ModelsImportForm = (...),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id,
        "workspace.models_import",
        request.app.state.config.USER_PERMISSIONS,
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    try:
        data = form_data.models
        if isinstance(data, list):
            for model_data in data:
                # Here, you can add logic to validate model_data if needed
                model_id = model_data.get("id")

                if model_id and is_valid_model_id(model_id):
                    existing_model = Models.get_model_by_id(model_id, db=db)
                    if existing_model:
                        # Update existing model
                        model_data["meta"] = model_data.get("meta", {})
                        model_data["params"] = model_data.get("params", {})

                        updated_model = ModelForm(
                            **{**existing_model.model_dump(), **model_data}
                        )
                        Models.update_model_by_id(model_id, updated_model, db=db)
                    else:
                        # Insert new model
                        model_data["meta"] = model_data.get("meta", {})
                        model_data["params"] = model_data.get("params", {})
                        new_model = ModelForm(**model_data)
                        Models.insert_new_model(
                            user_id=user.id, form_data=new_model, db=db
                        )
            return True
        else:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


############################
# SyncModels
############################


class SyncModelsForm(BaseModel):
    models: list[ModelModel] = []


@router.post("/sync", response_model=list[ModelModel])
async def sync_models(
    request: Request,
    form_data: SyncModelsForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    return Models.sync_models(user.id, form_data.models, db=db)


###########################
# GetModelById
###########################


class ModelIdForm(BaseModel):
    id: str


# Note: We're not using the typical url path param here, but instead using a query parameter to allow '/' in the id
@router.get("/model", response_model=Optional[ModelAccessResponse])
async def get_model_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    model = Models.get_model_by_id(id, db=db)
    if model:
        if (
            (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
            or model.user_id == user.id
            or has_access(user.id, "read", model.access_control, db=db)
        ):
            return ModelAccessResponse(
                **model.model_dump(),
                write_access=(
                    (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == model.user_id
                    or has_access(user.id, "write", model.access_control, db=db)
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


###########################
# GetModelById
###########################


@router.get("/model/profile/image")
def get_model_profile_image(
    request: Request,
    id: str,
    theme: Optional[str] = "light",
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    from open_webui.models.providers import Providers

    model = Models.get_model_by_id(id, db=db)

    if model:
        # Priority 1: Manual override (custom uploaded image)
        if model.meta and model.meta.profile_image_url:
            image_url = model.meta.profile_image_url

            # Skip default favicon - fall through to provider detection
            # Check for both relative and absolute paths to favicon
            is_default_favicon = (
                image_url == "/static/favicon.png"
                or image_url.endswith("/static/favicon.png")
            )

            if not is_default_favicon:
                # ETag based on model's updated_at for manual overrides
                etag = f'"{model.updated_at}"' if model.updated_at else None
                client_etag = request.headers.get("If-None-Match")

                # Check if client has cached version
                if etag and client_etag == etag:
                    return Response(status_code=status.HTTP_304_NOT_MODIFIED)

                if image_url.startswith("http"):
                    return Response(
                        status_code=status.HTTP_302_FOUND,
                        headers={"Location": image_url},
                    )
                elif image_url.startswith("data:image"):
                    try:
                        header, base64_data = image_url.split(",", 1)
                        image_data = base64.b64decode(base64_data)
                        image_buffer = io.BytesIO(image_data)
                        media_type = header.split(";")[0].lstrip("data:")

                        headers = {
                            "Content-Disposition": "inline",
                            "Cache-Control": "public, max-age=3600",
                        }
                        if etag:
                            headers["ETag"] = etag

                        return StreamingResponse(
                            image_buffer,
                            media_type=media_type,
                            headers=headers,
                        )
                    except Exception as e:
                        log.warning(f"Error decoding profile image: {e}")
                elif image_url.startswith("/"):
                    headers = {"Cache-Control": "public, max-age=3600"}
                    if etag:
                        headers["ETag"] = etag
                    return FileResponse(
                        f"{STATIC_DIR}{image_url}",
                        headers=headers,
                    )

        # Priority 2: Automatic provider logo detection
        # Determine owned_by from runtime model state or base_model_id
        owned_by = "openai"  # Default assumption for custom models

        # Try to get owned_by from runtime MODELS state (for base models)
        if hasattr(request.app.state, "MODELS") and request.app.state.MODELS:
            runtime_model = request.app.state.MODELS.get(model.id)
            if runtime_model and "owned_by" in runtime_model:
                owned_by = runtime_model.get("owned_by", "openai")
            elif model.base_model_id:
                # For custom presets, check the base model's owned_by
                base_runtime_model = request.app.state.MODELS.get(model.base_model_id)
                if base_runtime_model and "owned_by" in base_runtime_model:
                    owned_by = base_runtime_model.get("owned_by", "openai")

        provider_result = Providers.detect_provider_logo_with_metadata(model.id, owned_by, theme or "light", db=db)

        if provider_result:
            provider_logo = provider_result["logo_url"]
            provider_updated_at = provider_result["updated_at"]

            # ETag combines model and provider timestamps for cache invalidation
            etag = f'"{model.updated_at}-{provider_updated_at}"' if model.updated_at and provider_updated_at else None
            client_etag = request.headers.get("If-None-Match")

            # Check if client has cached version
            if etag and client_etag == etag:
                return Response(status_code=status.HTTP_304_NOT_MODIFIED)

            # Provider logo is HTTP URL - redirect
            if provider_logo.startswith("http"):
                headers = {
                    "Location": provider_logo,
                    "Cache-Control": "public, max-age=3600",
                }
                if etag:
                    headers["ETag"] = etag
                return Response(
                    status_code=status.HTTP_302_FOUND,
                    headers=headers,
                )
            # Provider logo is data URL - stream
            elif provider_logo.startswith("data:image"):
                try:
                    header, base64_data = provider_logo.split(",", 1)
                    image_data = base64.b64decode(base64_data)
                    image_buffer = io.BytesIO(image_data)
                    media_type = header.split(";")[0].lstrip("data:")

                    headers = {"Cache-Control": "public, max-age=3600"}
                    if etag:
                        headers["ETag"] = etag

                    return StreamingResponse(
                        image_buffer,
                        media_type=media_type,
                        headers=headers,
                    )
                except Exception as e:
                    log.warning(f"Error decoding provider logo: {e}")
            # Provider logo is relative path
            elif provider_logo.startswith("/"):
                headers = {"Cache-Control": "public, max-age=3600"}
                if etag:
                    headers["ETag"] = etag
                return FileResponse(
                    f"{STATIC_DIR}{provider_logo}",
                    headers=headers,
                )

    # Priority 3: Default fallback
    return FileResponse(f"{STATIC_DIR}/favicon.png")


@router.get("/model/profile/image/preview")
def get_model_profile_image_preview(
    request: Request,
    id: str,
    theme: Optional[str] = "light",
    profile_image_url: Optional[str] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Preview what the profile image would be with a given profile_image_url override.
    Used for showing immediate feedback in ModelEditor without saving.
    """
    from open_webui.models.providers import Providers

    model = Models.get_model_by_id(id, db=db)
    if not model:
        return FileResponse(f"{STATIC_DIR}/favicon.png")

    # If profile_image_url provided, use it for preview
    # Otherwise fall through to provider detection
    preview_url = profile_image_url if profile_image_url else (model.meta.profile_image_url if model.meta else None)

    # Priority 1: Manual override (if not default favicon)
    if preview_url:
        is_default_favicon = (
            preview_url == "/static/favicon.png"
            or preview_url.endswith("/static/favicon.png")
        )

        if not is_default_favicon:
            if preview_url.startswith("http"):
                return Response(
                    status_code=status.HTTP_302_FOUND,
                    headers={"Location": preview_url},
                )
            elif preview_url.startswith("data:image"):
                try:
                    header, base64_data = preview_url.split(",", 1)
                    image_data = base64.b64decode(base64_data)
                    image_buffer = io.BytesIO(image_data)
                    media_type = header.split(";")[0].lstrip("data:")
                    return StreamingResponse(
                        image_buffer,
                        media_type=media_type,
                        headers={"Cache-Control": "no-cache"},
                    )
                except Exception as e:
                    log.warning(f"Error decoding preview image: {e}")
            elif preview_url.startswith("/"):
                return FileResponse(
                    f"{STATIC_DIR}{preview_url}",
                    headers={"Cache-Control": "no-cache"},
                )

    # Priority 2: Provider logo detection
    owned_by = "openai"
    if hasattr(request.app.state, "MODELS") and request.app.state.MODELS:
        runtime_model = request.app.state.MODELS.get(model.id)
        if runtime_model and "owned_by" in runtime_model:
            owned_by = runtime_model.get("owned_by", "openai")
        elif model.base_model_id:
            base_runtime_model = request.app.state.MODELS.get(model.base_model_id)
            if base_runtime_model and "owned_by" in base_runtime_model:
                owned_by = base_runtime_model.get("owned_by", "openai")

    provider_result = Providers.detect_provider_logo_with_metadata(
        model.id, owned_by, theme or "light", db=db
    )

    if provider_result:
        provider_logo = provider_result["logo_url"]
        if provider_logo.startswith("http"):
            return Response(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": provider_logo, "Cache-Control": "no-cache"},
            )
        elif provider_logo.startswith("data:image"):
            try:
                header, base64_data = provider_logo.split(",", 1)
                image_data = base64.b64decode(base64_data)
                image_buffer = io.BytesIO(image_data)
                media_type = header.split(";")[0].lstrip("data:")
                return StreamingResponse(
                    image_buffer,
                    media_type=media_type,
                    headers={"Cache-Control": "no-cache"},
                )
            except Exception as e:
                log.warning(f"Error decoding provider logo: {e}")
        elif provider_logo.startswith("/"):
            return FileResponse(
                f"{STATIC_DIR}{provider_logo}",
                headers={"Cache-Control": "no-cache"},
            )

    # Priority 3: Default fallback
    return FileResponse(f"{STATIC_DIR}/favicon.png")


############################
# ToggleModelById
############################


@router.post("/model/toggle", response_model=Optional[ModelResponse])
async def toggle_model_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    model = Models.get_model_by_id(id, db=db)
    if model:
        if (
            user.role == "admin"
            or model.user_id == user.id
            or has_access(user.id, "write", model.access_control, db=db)
        ):
            model = Models.toggle_model_by_id(id, db=db)

            if model:
                return model
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateModelById
############################


@router.post("/model/update", response_model=Optional[ModelModel])
async def update_model_by_id(
    form_data: ModelForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    model = Models.get_model_by_id(form_data.id, db=db)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        model.user_id != user.id
        and not has_access(user.id, "write", model.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    model = Models.update_model_by_id(
        form_data.id, ModelForm(**form_data.model_dump()), db=db
    )
    return model


############################
# DeleteModelById
############################


@router.post("/model/delete", response_model=bool)
async def delete_model_by_id(
    form_data: ModelIdForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    model = Models.get_model_by_id(form_data.id, db=db)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and model.user_id != user.id
        and not has_access(user.id, "write", model.access_control, db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Models.delete_model_by_id(form_data.id, db=db)
    return result


@router.delete("/delete/all", response_model=bool)
async def delete_all_models(
    user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    result = Models.delete_all_models(db=db)
    return result
