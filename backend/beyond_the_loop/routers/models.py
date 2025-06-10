import uuid
from typing import Optional

from beyond_the_loop.models.models import (
    ModelForm,
    ModelModel,
    ModelResponse,
    ModelUserResponse,
    Models,
    TagResponse
)
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission

router = APIRouter()


###########################
# GetModels
###########################


@router.get("/", response_model=list[ModelUserResponse])
async def get_models(user=Depends(get_verified_user)):
    models = Models.get_models_by_user_and_company(user.id, user.company_id)
    sorted_models = sorted(models, key=lambda m: not m.bookmarked_by_user)
    return sorted_models


###########################
# GetBaseModels
###########################


@router.get("/base", response_model=list[ModelResponse])
async def get_base_models(user=Depends(get_admin_user)):
    return Models.get_base_models_by_comany_and_user(user.company_id, user.id, user.role)


############################
# CreateNewModel
############################


@router.post("/create", response_model=Optional[ModelModel])
async def create_new_model(
    request: Request,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.models", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    model = Models.get_model_by_name_and_company(form_data.name, user.company_id)
    if model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.MODEL_NAME_TAKEN,
        )

    else:
        form_data.id = str(uuid.uuid4())

        model = Models.insert_new_model(form_data, user.id, user.company_id)
        if model:
            return model
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.DEFAULT(),
            )


###########################
# GetModelById
###########################


# Note: We're not using the typical url path param here, but instead using a query parameter to allow '/' in the id
@router.get("/model", response_model=Optional[ModelResponse])
async def get_model_by_id(id: str, user=Depends(get_verified_user)):
    model = Models.get_model_by_id(id)
    if model:
        if (
            model.user_id == user.id
            or has_access(user.id, "read", model.access_control)
        ):
            return model
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToggelModelById
############################


@router.post("/model/toggle", response_model=Optional[ModelResponse])
async def toggle_model_by_id(id: str, user=Depends(get_verified_user)):
    model = Models.get_model_by_id(id)
    if model:
        if (
            model.user_id == user.id
            or has_access(user.id, "write", model.access_control)
        ):
            model = Models.toggle_model_by_id_and_company(id, user.company_id)

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

#################################
# Add and remove from bookmarked
#################################

@router.post("/model/{model}/bookmark/update")
async def update_model_bookmark(model: str, user=Depends(get_verified_user)):
    model = Models.get_model_by_id(model)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    bookmarked =Models.toggle_bookmark(model.id, user.id)
    return {"model_id": model.id, "bookmarked_by_user": bookmarked}

############################
# UpdateModelById
############################

@router.post("/model/update", response_model=Optional[ModelModel])
async def update_model_by_id(
    id: str,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    model = Models.get_model_by_id(id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        (not model.base_model_id and user.role != "admin")
        and model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    model = Models.update_model_by_id_and_company(id, form_data, user.company_id)
    return model


@router.post("/model/update", response_model=Optional[ModelModel])
async def update_model_by_id(
    id: str,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    model = Models.get_model_by_id(id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        (not model.base_model_id and user.role != "admin")
        and model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    model = Models.update_model_by_id_and_company(id, form_data, user.company_id)
    return model


############################
# DeleteModelById
############################


@router.delete("/model/delete", response_model=bool)
async def delete_model_by_id(id: str, user=Depends(get_verified_user)):
    model = Models.get_model_by_id(id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Models.delete_model_by_id_and_company(id, user.company_id)
    return result

############################
# GetUserTags
############################

@router.get("/user-tags", response_model=list[TagResponse])
async def get_user_tags(user=Depends(get_verified_user)):
    tags = Models.get_system_and_user_tags(user.id)
    if not tags:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return tags