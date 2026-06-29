import logging
import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from open_webui.config import UPLOAD_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.config import Config
from open_webui.models.chats import Chats
from open_webui.models.folders import (
    FolderForm,
    FolderModel,
    FolderNameIdResponse,
    Folders,
    FolderUpdateForm,
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import Users
from open_webui.utils.access_control import has_permission
from open_webui.utils.access_control import (
    filter_allowed_access_grants,
)
from open_webui.utils.access_control.files import get_accessible_folder_files
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


router = APIRouter()


from open_webui.utils.access_control.folders import has_folder_access as _has_folder_access


async def check_folders_permission(request: Request, user, db=None):
    """Verify the folders feature is enabled and the user has permission."""
    config = await Config.get_many('folders.enable', 'user.permissions')
    if config.get('folders.enable') is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    if user.role != 'admin' and not await has_permission(
        user.id,
        'features.folders',
        config.get('user.permissions'),
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# Get Folders
############################


@router.get('/', response_model=list[FolderNameIdResponse])
async def get_folders(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)

    folders = await Folders.get_folders_by_user_id(user.id, db=db)

    # Verify folder data integrity
    folder_list = []
    for folder in folders:
        if folder.parent_id and not await Folders.get_folder_by_id_and_user_id(folder.parent_id, user.id, db=db):
            folder = await Folders.update_folder_parent_id_by_id_and_user_id(folder.id, user.id, None, db=db)

        if folder.data and 'files' in folder.data:
            accessible_files = await get_accessible_folder_files(folder.data['files'], user, db=db)
            if len(accessible_files) != len(folder.data.get('files', [])):
                folder.data['files'] = accessible_files
                await Folders.update_folder_by_id_and_user_id(
                    folder.id, user.id, FolderUpdateForm(data=folder.data), db=db
                )

        folder_list.append(FolderNameIdResponse(**folder.model_dump()))

    return folder_list


############################
# Create Folder
############################


@router.post('/')
async def create_folder(
    request: Request,
    form_data: FolderForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_parent_id_and_user_id_and_name(
        form_data.parent_id, user.id, form_data.name, db=db
    )

    if folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Folder already exists'),
        )

    # Check if creating a subfolder in a shared folder
    if form_data.parent_id:
        parent = await Folders.get_folder_by_id(form_data.parent_id, db=db)
        if parent and parent.user_id != user.id:
            # Creating subfolder in someone else's shared folder
            if user.role != 'admin' and not await _has_folder_access(user.id, parent, 'write', db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
            # Create as the folder owner's subfolder (keep tree consistent)
            try:
                folder = await Folders.insert_new_folder(parent.user_id, form_data, form_data.parent_id, db=db)
                await publish_event(
                    request,
                    EVENTS.FOLDER_CREATED,
                    actor=user,
                    subject_id=folder.id,
                    data={'name': folder.name, 'parent_id': folder.parent_id, 'owner_id': folder.user_id},
                )
                return folder
            except Exception as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error creating folder'),
                )

    try:
        folder = await Folders.insert_new_folder(user.id, form_data, form_data.parent_id, db=db)
        await publish_event(
            request,
            EVENTS.FOLDER_CREATED,
            actor=user,
            subject_id=folder.id,
            data={'name': folder.name, 'parent_id': folder.parent_id, 'owner_id': folder.user_id},
        )
        return folder
    except Exception as e:
        log.exception(e)
        log.error('Error creating folder')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error creating folder'),
        )


############################
# Get Shared Folders
############################


@router.get('/shared')
async def get_shared_folders(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get all folders shared with the current user (not owned by them)."""
    await check_folders_permission(request, user, db=db)
    groups = await Groups.get_groups_by_member_id(user.id, db=db)
    group_ids = {g.id for g in groups}

    folder_perms = await Folders.get_shared_folder_ids_for_user(user.id, group_ids, db=db)

    # Filter out folders owned by the user
    results = []
    owner_cache = {}
    for folder_id, permission in folder_perms.items():
        folder = await Folders.get_folder_by_id(folder_id, db=db)
        if not folder or folder.user_id == user.id:
            continue

        # Get owner name (cached)
        if folder.user_id not in owner_cache:
            owner = await Users.get_user_by_id(folder.user_id, db=db)
            owner_cache[folder.user_id] = owner.name if owner else 'Unknown'

        results.append(
            {
                **folder.model_dump(),
                'owner_name': owner_cache[folder.user_id],
                'permission': permission,
            }
        )

    # Also include child folders of shared folders (inheritance)
    shared_root_ids = {r['id'] for r in results}
    for root_id in list(shared_root_ids):
        root_folder = await Folders.get_folder_by_id(root_id, db=db)
        if root_folder:
            children = await Folders.get_children_folders_by_id_and_user_id(root_id, root_folder.user_id, db=db)
            if children:
                for child in children:
                    if child.id not in {r['id'] for r in results}:
                        results.append(
                            {
                                **child.model_dump(),
                                'owner_name': owner_cache.get(child.user_id, 'Unknown'),
                                'permission': folder_perms.get(root_id, 'read'),
                            }
                        )

    return results


############################
# Get Folders By Id
############################


@router.get('/{id}', response_model=None)
async def get_folder_by_id(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id_and_user_id(id, user.id, db=db)
    if folder:
        grants = await AccessGrants.get_grants_by_resource('folder', id, db=db)
        return {**folder.model_dump(), 'access_grants': [g.model_dump() for g in grants]}

    # Check shared access
    folder = await Folders.get_folder_by_id(id, db=db)
    if folder and (user.role == 'admin' or await _has_folder_access(user.id, folder, 'read', db)):
        grants = await AccessGrants.get_grants_by_resource('folder', id, db=db)
        return {**folder.model_dump(), 'access_grants': [g.model_dump() for g in grants]}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


############################
# Update Folder Name By Id
############################


@router.post('/{id}/update')
async def update_folder_name_by_id(
    request: Request,
    id: str,
    form_data: FolderUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id_and_user_id(id, user.id, db=db)
    if not folder:
        # Check shared write access
        folder = await Folders.get_folder_by_id(id, db=db)
        if not folder or (user.role != 'admin' and not await _has_folder_access(user.id, folder, 'write', db)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    if folder:
        if form_data.name is not None:
            # Check if folder with same name exists
            existing_folder = await Folders.get_folder_by_parent_id_and_user_id_and_name(
                folder.parent_id, folder.user_id, form_data.name, db=db
            )
            if existing_folder and existing_folder.id != id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Folder already exists'),
                )

        # Validate read access to every file/collection being attached.
        # Folder files are consumed by chat middleware as RAG context.
        if form_data.data and isinstance(form_data.data.get('files'), list):
            accessible_files = await get_accessible_folder_files(form_data.data['files'], user, db=db)
            if len(accessible_files) != len(form_data.data['files']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )

        try:
            folder = await Folders.update_folder_by_id_and_user_id(id, folder.user_id, form_data, db=db)
            await publish_event(
                request,
                EVENTS.FOLDER_UPDATED,
                actor=user,
                subject_id=id,
                data={'name': folder.name},
            )
            return folder
        except Exception as e:
            log.exception(e)
            log.error(f'Error updating folder: {id}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating folder'),
            )


############################
# Update Folder Parent Id By Id
############################


class FolderParentIdForm(BaseModel):
    parent_id: Optional[str] = None


@router.post('/{id}/update/parent')
async def update_folder_parent_id_by_id(
    request: Request,
    id: str,
    form_data: FolderParentIdForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id_and_user_id(id, user.id, db=db)
    if folder:
        existing_folder = await Folders.get_folder_by_parent_id_and_user_id_and_name(
            form_data.parent_id, user.id, folder.name, db=db
        )

        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Folder already exists'),
            )

        try:
            folder = await Folders.update_folder_parent_id_by_id_and_user_id(id, user.id, form_data.parent_id, db=db)
            await publish_event(
                request,
                EVENTS.FOLDER_PARENT_UPDATED,
                actor=user,
                subject_id=id,
                data={'parent_id': form_data.parent_id},
            )
            return folder
        except Exception as e:
            log.exception(e)
            log.error(f'Error updating folder: {id}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating folder'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update Folder Is Expanded By Id
############################


class FolderIsExpandedForm(BaseModel):
    is_expanded: bool


@router.post('/{id}/update/expanded')
async def update_folder_is_expanded_by_id(
    request: Request,
    id: str,
    form_data: FolderIsExpandedForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id_and_user_id(id, user.id, db=db)
    if folder:
        try:
            folder = await Folders.update_folder_is_expanded_by_id_and_user_id(
                id, user.id, form_data.is_expanded, db=db
            )
            return folder
        except Exception as e:
            log.exception(e)
            log.error(f'Error updating folder: {id}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating folder'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update Folder Access By Id
############################


class FolderAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/{id}/access/update')
async def update_folder_access_by_id(
    request: Request,
    id: str,
    form_data: FolderAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id(id, db=db)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner, admin, or write-granted user can update access
    if user.role != 'admin' and user.id != folder.user_id:
        if not await _has_folder_access(user.id, folder, 'write', db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        None,
        db=db,
    )

    await AccessGrants.set_access_grants('folder', id, form_data.access_grants, db=db)

    grants = await AccessGrants.get_grants_by_resource('folder', id, db=db)
    await publish_event(
        request,
        EVENTS.FOLDER_ACCESS_UPDATED,
        actor=user,
        subject_id=id,
        data={'grant_count': len(grants)},
    )
    return {
        **folder.model_dump(),
        'access_grants': [g.model_dump() for g in grants],
    }


############################
# Get Shared Folder Chats
############################


@router.get('/{id}/shared/chats')
async def get_shared_folder_chats(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get chats within a shared folder. Returns readonly flag based on permission."""
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id(id, db=db)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    is_owner = user.id == folder.user_id
    is_admin = user.role == 'admin'
    has_write = is_owner or is_admin or await _has_folder_access(user.id, folder, 'write', db)
    has_read = has_write or await _has_folder_access(user.id, folder, 'read', db)

    if not has_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chats = await Chats.get_all_chats_by_folder_id(id, db=db)

    # Resolve owner names for display (avatar URLs are constructed client-side)
    owner_cache: dict[str, str] = {}
    for chat in chats:
        uid = chat['user_id']
        if uid not in owner_cache:
            u = await Users.get_user_by_id(uid, db=db)
            owner_cache[uid] = u.name if u else 'Unknown'
        chat['owner_name'] = owner_cache[uid]

    return {
        'chats': [{**chat, 'readonly': chat['user_id'] != user.id} for chat in chats],
        'folder_permission': 'write' if has_write else 'read',
    }


############################
# Delete Folder By Id
############################


@router.delete('/{id}')
async def delete_folder_by_id(
    request: Request,
    id: str,
    delete_contents: Optional[bool] = True,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folders_permission(request, user, db=db)
    folder = await Folders.get_folder_by_id_and_user_id(id, user.id, db=db)

    if not folder:
        # Check if it's a shared subfolder with write access
        folder = await Folders.get_folder_by_id(id, db=db)
        if folder and folder.parent_id:
            if user.role != 'admin' and not await _has_folder_access(user.id, folder, 'write', db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
        elif folder and not folder.parent_id:
            # Root shared folders can only be deleted by owner/admin
            if user.role != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    folder_owner_id = folder.user_id

    folder_ids = await Folders.get_folder_ids_by_id_and_user_id_in_subtree(id, folder_owner_id, db=db)
    if await Chats.count_chats_by_folder_ids_and_user_id(folder_ids, folder_owner_id, db=db):
        chat_delete_permission = await has_permission(
            user.id, 'chat.delete', await Config.get('user.permissions'), db=db
        )
        if user.role != 'admin' and not chat_delete_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    folders = []
    folders.append(folder)
    while folders:
        folder = folders.pop()
        if folder:
            try:
                folder_ids = await Folders.delete_folder_by_id_and_user_id(folder.id, folder_owner_id, db=db)

                for folder_id in folder_ids:
                    if delete_contents:
                        await Chats.delete_chats_by_user_id_and_folder_id(folder_owner_id, folder_id, db=db)
                    else:
                        await Chats.move_chats_by_user_id_and_folder_id(folder_owner_id, folder_id, None, db=db)

                    # Clean up access grants for this folder
                    await AccessGrants.revoke_all_access('folder', folder_id, db=db)

                await publish_event(
                    request,
                    EVENTS.FOLDER_DELETED,
                    actor=user,
                    subject_id=id,
                    data={'folder_ids': folder_ids, 'delete_contents': delete_contents},
                )
                return True
            except Exception as e:
                log.exception(e)
                log.error(f'Error deleting folder: {id}')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error deleting folder'),
                )
            finally:
                # Get all subfolders
                subfolders = await Folders.get_folders_by_parent_id_and_user_id(folder.id, folder_owner_id, db=db)
                folders.extend(subfolders)

    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
