import logging
import posixpath
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from open_webui.config import STORAGE_PROVIDER, S3_BUCKET_NAME
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.tenants import (
    Tenants,
    TenantForm,
    TenantUpdateForm,
    get_default_help_text,
)
from open_webui.models.users import Users
from open_webui.services.s3 import (
    get_s3_client,
    upload_fileobj,
    delete_object,
    generate_presigned_url,
)
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class TenantInfo(BaseModel):
    id: str
    name: str
    s3_bucket: str
    table_name: Optional[str] = None
    system_config_client_name: Optional[str] = None
    logo_image_url: Optional[str] = None
    help_text: str
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class PromptFile(BaseModel):
    key: str
    size: int
    last_modified: Optional[str] = None
    url: str


class PromptDeleteRequest(BaseModel):
    key: str


class TenantPromptUploadResponse(BaseModel):
    bucket: str
    key: str
    url: str


class DefaultHelpResponse(BaseModel):
    help_text: str


@router.get("", response_model=list[TenantInfo])
def list_tenants(admin=Depends(get_admin_user)):
    tenants = Tenants.get_tenants()
    return [TenantInfo(**tenant.model_dump()) for tenant in tenants]


@router.get("/default-help", response_model=DefaultHelpResponse)
def get_default_help():
    return DefaultHelpResponse(help_text=get_default_help_text())


@router.post("", response_model=TenantInfo)
def create_tenant(form_data: TenantForm, admin=Depends(get_admin_user)):
    try:
        tenant = Tenants.create_tenant(form_data)
    except Exception as exc:
        log.exception("Failed to create tenant: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create tenant.",
        )
    return TenantInfo(**tenant.model_dump())


@router.patch("/{tenant_id}", response_model=TenantInfo)
def update_tenant(tenant_id: str, form_data: TenantUpdateForm, admin=Depends(get_admin_user)):
    existing = Tenants.get_tenant_by_id(tenant_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    try:
        tenant = Tenants.update_tenant(tenant_id, form_data)
    except Exception as exc:
        log.exception("Failed to update tenant: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update tenant.",
        )

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    return TenantInfo(**tenant.model_dump())


@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: str, admin=Depends(get_admin_user)):
    tenant = Tenants.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    if Users.count_users_by_tenant(tenant_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tenant with assigned users.",
        )

    Tenants.delete_tenant(tenant_id)
    return {"status": "deleted", "id": tenant_id}


@router.post(
    "/{tenant_id}/prompts",
    response_model=TenantPromptUploadResponse,
)
async def upload_tenant_prompt(
    tenant_id: str, file: UploadFile = File(...), admin=Depends(get_admin_user)
):
    if STORAGE_PROVIDER != "s3":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="S3 storage provider is not configured on this deployment.",
        )

    if not S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket name is not configured.",
        )

    tenant = Tenants.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    bucket_prefix = tenant.s3_bucket.rstrip("/")
    if not bucket_prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant does not have an S3 bucket configured.",
        )

    safe_name = posixpath.basename(file.filename or "prompt.txt")
    if not safe_name.lower().endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files may be uploaded to prompts.",
        )

    object_key = posixpath.join(bucket_prefix, "prompts", safe_name)
    extra_args = {"ContentType": file.content_type or "text/plain"}

    try:
        upload_fileobj(file.file, S3_BUCKET_NAME, object_key, extra_args)
    except ClientError as exc:
        log.exception("Failed uploading tenant prompt to S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload prompt file.",
        )

    url = generate_presigned_url(S3_BUCKET_NAME, object_key)

    return TenantPromptUploadResponse(bucket=S3_BUCKET_NAME, key=object_key, url=url)


@router.get("/{tenant_id}/prompts", response_model=list[PromptFile])
def list_tenant_prompts(tenant_id: str, admin=Depends(get_admin_user)):
    if STORAGE_PROVIDER != "s3":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="S3 storage provider is not configured on this deployment.",
        )

    if not S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket name is not configured.",
        )

    tenant = Tenants.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    bucket_prefix = tenant.s3_bucket.rstrip("/")
    if not bucket_prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant does not have an S3 bucket configured.",
        )

    list_prefix = posixpath.join(bucket_prefix, "prompts") + "/"
    s3_client = get_s3_client()
    paginator = s3_client.get_paginator("list_objects_v2")
    files: list[PromptFile] = []

    try:
        for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=list_prefix):
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if not key or key.endswith("/"):
                    continue

                url = generate_presigned_url(S3_BUCKET_NAME, key)

                last_modified = obj.get("LastModified")
                files.append(
                    PromptFile(
                        key=key,
                        size=obj.get("Size", 0),
                        last_modified=last_modified.isoformat()
                        if last_modified
                        else None,
                        url=url,
                    )
                )
    except ClientError as exc:
        log.exception("Failed to list tenant prompts from S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenant prompts.",
        )

    return files


@router.delete("/{tenant_id}/prompts")
def delete_tenant_prompt(
    tenant_id: str, form_data: PromptDeleteRequest, admin=Depends(get_admin_user)
):
    if STORAGE_PROVIDER != "s3":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="S3 storage provider is not configured on this deployment.",
        )

    if not S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket name is not configured.",
        )

    tenant = Tenants.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    bucket_prefix = tenant.s3_bucket.rstrip("/")
    prompts_prefix = posixpath.join(bucket_prefix, "prompts") + "/"

    key = form_data.key
    if not key or not key.startswith(prompts_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid prompt key.",
        )

    try:
        delete_object(S3_BUCKET_NAME, key)
    except ClientError as exc:
        log.exception("Failed to delete tenant prompt from S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant prompt.",
        )

    return {"status": "deleted", "key": key}


@router.get("/{tenant_id}", response_model=TenantInfo)
def get_tenant_detail(tenant_id: str, user=Depends(get_verified_user)):
    tenant = Tenants.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    if user.role != "admin" and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tenant.",
        )

    return TenantInfo(**tenant.model_dump())
