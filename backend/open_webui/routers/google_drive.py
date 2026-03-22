"""
Google Drive Router for Open WebUI.

Provides API endpoints for:
- Linking Google Drive folders to knowledge bases
- Syncing files from Google Drive
- Managing external resources

Security:
- All endpoints require user authentication
- Users can only access resources they own or have access to via knowledge base permissions
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_session
from open_webui.models.external_resources import (
    ExternalResourceCreateForm,
    ExternalResourceResponse,
    ExternalResources,
    ExternalResourceUpdateForm,
)
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.access_grants import AccessGrants
from open_webui.routers.retrieval import process_file, ProcessFileForm
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_verified_user
from open_webui.utils.google_drive import (
    GoogleDriveError,
    GoogleDriveAuthError,
    GoogleDriveNotFoundError,
    GoogleDrivePermissionError,
    GoogleDriveRateLimitError,
    google_drive_service,
)

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Response Models
############################


class GoogleDriveStatusResponse(BaseModel):
    """Response for Google Drive configuration status."""

    configured: bool
    message: str


class FolderValidationResponse(BaseModel):
    """Response for folder validation."""

    valid: bool
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    file_count: int = 0
    message: str


class SyncResult(BaseModel):
    """Result of a sync operation."""

    success: bool
    files_added: int = 0
    files_failed: int = 0
    errors: list[str] = []
    message: str


class ExternalResourceListResponse(BaseModel):
    """Response for listing external resources."""

    items: list[ExternalResourceResponse]
    total: int


############################
# Helper Functions
############################


def _check_knowledge_access(
    knowledge_id: str,
    user_id: str,
    user_role: str,
    permission: str = 'write',
    db: Session = None,
) -> bool:
    """Check if user has access to a knowledge base."""
    knowledge = Knowledges.get_knowledge_by_id(knowledge_id, db=db)
    if not knowledge:
        return False

    if knowledge.user_id == user_id:
        return True

    if user_role == 'admin':
        return True

    return AccessGrants.has_access(
        user_id=user_id,
        resource_type='knowledge',
        resource_id=knowledge_id,
        permission=permission,
        db=db,
    )


############################
# Status Endpoint
############################


@router.get('/status', response_model=GoogleDriveStatusResponse)
async def get_google_drive_status(user=Depends(get_verified_user)):
    """
    Check if Google Drive integration is configured.

    Returns configuration status and any setup instructions if not configured.
    """
    if google_drive_service.is_configured():
        return GoogleDriveStatusResponse(
            configured=True,
            message='Google Drive integration is configured and ready to use.',
        )
    else:
        return GoogleDriveStatusResponse(
            configured=False,
            message='Google Drive integration is not configured. Please set GOOGLE_DRIVE_CREDENTIALS_PATH environment variable.',
        )


############################
# Folder Validation
############################


@router.post('/validate-folder', response_model=FolderValidationResponse)
async def validate_google_drive_folder(
    request: Request,
    user=Depends(get_verified_user),
):
    """
    Validate a Google Drive folder URL or ID.

    Checks if the folder exists, is accessible, and contains supported files.
    """
    try:
        body = await request.json()
        folder_url = body.get('folder_url', '')
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid request body',
        )

    if not folder_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='folder_url is required',
        )

    # Extract folder ID
    folder_id = google_drive_service.extract_folder_id(folder_url)
    if not folder_id:
        return FolderValidationResponse(
            valid=False,
            message='Invalid Google Drive folder URL or ID. Please provide a valid Google Drive folder link.',
        )

    try:
        # Validate folder access
        folder = google_drive_service.validate_folder_access(folder_id)

        # Count supported files
        files, _ = google_drive_service.list_files(folder_id, supported_types_only=True)

        return FolderValidationResponse(
            valid=True,
            folder_id=folder.id,
            folder_name=folder.name,
            file_count=len(files),
            message=f'Found {len(files)} supported files in folder "{folder.name}".',
        )

    except GoogleDriveAuthError as e:
        return FolderValidationResponse(
            valid=False,
            message=f'Authentication error: {e}',
        )
    except GoogleDriveNotFoundError:
        return FolderValidationResponse(
            valid=False,
            message='Folder not found. Please check the URL and make sure the folder exists.',
        )
    except GoogleDrivePermissionError:
        return FolderValidationResponse(
            valid=False,
            message='Cannot access folder. Make sure the folder is shared with the service account.',
        )
    except GoogleDriveRateLimitError:
        return FolderValidationResponse(
            valid=False,
            message='Google Drive API rate limit exceeded. Please try again later.',
        )
    except GoogleDriveError as e:
        log.error(f'Google Drive error validating folder: {e}')
        return FolderValidationResponse(
            valid=False,
            message=f'Error accessing Google Drive: {e}',
        )


############################
# Resource Management
############################


@router.post('/link', response_model=ExternalResourceResponse)
async def link_google_drive_folder(
    form_data: ExternalResourceCreateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Link a Google Drive folder to a knowledge base.

    Creates an external resource that can be synced to import files.
    """
    # Check knowledge base access
    if not _check_knowledge_access(form_data.knowledge_id, user.id, user.role, 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Extract and validate folder ID
    folder_id = google_drive_service.extract_folder_id(form_data.resource_link)
    if not folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid Google Drive folder URL or ID.',
        )

    try:
        # Validate folder access
        folder = google_drive_service.validate_folder_access(folder_id)

        # Update form with extracted folder ID and name
        form_data.resource_link = folder_id
        if not form_data.resource_name:
            form_data.resource_name = folder.name

        # Create external resource
        resource = ExternalResources.insert_new_resource(user.id, form_data, db=db)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to create external resource.',
            )

        return resource

    except GoogleDriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Google Drive folder not found.',
        )
    except GoogleDrivePermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Cannot access Google Drive folder. Make sure it is shared.',
        )
    except GoogleDriveError as e:
        log.error(f'Google Drive error linking folder: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Google Drive error: {e}',
        )


@router.get('/resources/{knowledge_id}', response_model=ExternalResourceListResponse)
async def get_knowledge_external_resources(
    knowledge_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all external resources linked to a knowledge base."""
    # Check knowledge base access
    if not _check_knowledge_access(knowledge_id, user.id, user.role, 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    resources = ExternalResources.get_resources_by_knowledge_id(knowledge_id, db=db)
    return ExternalResourceListResponse(items=resources, total=len(resources))


@router.get('/resource/{resource_id}', response_model=ExternalResourceResponse)
async def get_external_resource(
    resource_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get details of a specific external resource."""
    resource = ExternalResources.get_resource_by_id(resource_id, db=db)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check knowledge base access
    if not _check_knowledge_access(resource.knowledge_id, user.id, user.role, 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return resource


@router.patch('/resource/{resource_id}', response_model=ExternalResourceResponse)
async def update_external_resource(
    resource_id: str,
    form_data: ExternalResourceUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Update an external resource's settings."""
    resource = ExternalResources.get_resource_by_id(resource_id, db=db)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check knowledge base access
    if not _check_knowledge_access(resource.knowledge_id, user.id, user.role, 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    updated = ExternalResources.update_resource(resource_id, form_data, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to update external resource.',
        )

    return updated


@router.delete('/resource/{resource_id}')
async def delete_external_resource(
    resource_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Delete an external resource."""
    resource = ExternalResources.get_resource_by_id(resource_id, db=db)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check knowledge base access
    if not _check_knowledge_access(resource.knowledge_id, user.id, user.role, 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    success = ExternalResources.delete_resource_by_id(resource_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to delete external resource.',
        )

    return {'success': True, 'message': 'External resource deleted.'}


############################
# Sync Operations
############################


@router.post('/resource/{resource_id}/sync', response_model=SyncResult)
async def sync_external_resource(
    request: Request,
    resource_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Sync files from a Google Drive folder to the knowledge base.

    Downloads new/modified files and adds them to the knowledge base.
    """
    resource = ExternalResources.get_resource_by_id(resource_id, db=db)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check knowledge base access
    if not _check_knowledge_access(resource.knowledge_id, user.id, user.role, 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Update sync status
    ExternalResources.update_sync_status(resource_id, 'in_progress', db=db)

    files_added = 0
    files_failed = 0
    errors = []

    try:
        # List files from Google Drive
        files, _ = google_drive_service.list_files(
            resource.resource_link,
            supported_types_only=True,
        )

        for drive_file in files:
            try:
                # Download file content
                content, mime_type = google_drive_service.download_file(
                    drive_file.id,
                    drive_file.mime_type,
                )

                # Determine filename extension based on mime type
                ext_map = {
                    'application/pdf': '.pdf',
                    'text/plain': '.txt',
                    'text/csv': '.csv',
                    'text/markdown': '.md',
                }
                ext = ext_map.get(mime_type, '')
                filename = drive_file.name
                if ext and not filename.lower().endswith(ext):
                    filename = f'{filename}{ext}'

                # Save to storage
                file_id = Storage.upload_file(
                    file=content,
                    filename=filename,
                )

                # Create file record
                file_record = Files.insert_new_file(
                    user_id=user.id,
                    form_data={
                        'id': file_id,
                        'filename': filename,
                        'path': file_id,
                        'meta': {
                            'source': 'google_drive',
                            'drive_file_id': drive_file.id,
                            'external_resource_id': resource_id,
                        },
                    },
                    db=db,
                )

                if file_record:
                    # Process and add to knowledge base
                    try:
                        process_file(
                            request,
                            ProcessFileForm(
                                file_id=file_record.id,
                                collection_name=resource.knowledge_id,
                            ),
                            user=user,
                            db=db,
                        )
                        Knowledges.add_file_to_knowledge_by_id(
                            knowledge_id=resource.knowledge_id,
                            file_id=file_record.id,
                            user_id=user.id,
                            db=db,
                        )
                        files_added += 1
                    except Exception as e:
                        log.error(f'Failed to process file {filename}: {e}')
                        files_failed += 1
                        errors.append(f'{filename}: {e}')
                else:
                    files_failed += 1
                    errors.append(f'{filename}: Failed to create file record')

            except Exception as e:
                log.error(f'Failed to download/save file {drive_file.name}: {e}')
                files_failed += 1
                errors.append(f'{drive_file.name}: {e}')

        # Update sync status
        if files_failed == 0:
            ExternalResources.update_sync_status(resource_id, 'success', db=db)
        else:
            ExternalResources.update_sync_status(
                resource_id,
                'partial',
                error=f'{files_failed} files failed',
                db=db,
            )

        return SyncResult(
            success=True,
            files_added=files_added,
            files_failed=files_failed,
            errors=errors[:10],  # Limit errors in response
            message=f'Synced {files_added} files successfully. {files_failed} files failed.',
        )

    except GoogleDriveRateLimitError:
        ExternalResources.update_sync_status(resource_id, 'failed', error='Rate limit exceeded', db=db)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Google Drive API rate limit exceeded. Please try again later.',
        )
    except GoogleDriveError as e:
        ExternalResources.update_sync_status(resource_id, 'failed', error=str(e), db=db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Google Drive error: {e}',
        )
    except Exception as e:
        log.error(f'Sync failed for resource {resource_id}: {e}')
        ExternalResources.update_sync_status(resource_id, 'failed', error=str(e), db=db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Sync failed: {e}',
        )
