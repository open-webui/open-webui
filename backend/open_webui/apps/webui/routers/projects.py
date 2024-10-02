import json
from typing import Optional, Union
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status


from open_webui.apps.webui.models.projects import (
    Projects,
    ProjectModel,
    ProjectForm,
    ProjectResponse,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.utils import get_admin_user, get_verified_user

router = APIRouter()

############################
# GetProjects
############################


@router.get("/", response_model=Optional[Union[list[ProjectResponse], ProjectResponse]])
async def get_projects(id: Optional[str] = None, user=Depends(get_verified_user)):
    if id:
        project = Projects.get_project_by_id(id=id)

        if project:
            return project
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        return [
            ProjectResponse(**project.model_dump())
            for project in Projects.get_projects()
        ]


############################
# CreateNewProject
############################


@router.post("/create", response_model=Optional[ProjectResponse])
async def create_new_project(form_data: ProjectForm, user=Depends(get_admin_user)):
    project = Projects.get_project_by_id(form_data.id)
    if project is None:
        project = Projects.insert_new_project(user.id, form_data)

        if project:
            return project
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.FILE_EXISTS,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# UpdateProjectById
############################


@router.post("/update", response_model=Optional[ProjectResponse])
async def update_project_by_id(
    form_data: ProjectForm,
    user=Depends(get_admin_user),
):
    project = Projects.update_project_by_id(form_data)
    if project:
        return project
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# DeleteProjectById
############################


@router.delete("/delete", response_model=bool)
async def delete_project_by_id(id: str, user=Depends(get_admin_user)):
    result = Projects.delete_project_by_id(id=id)
    return result
