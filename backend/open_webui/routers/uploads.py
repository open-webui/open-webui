import logging
import os
import posixpath
import re
import uuid
from typing import Literal, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from open_webui.config import (
    STORAGE_PROVIDER,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_REGION_NAME,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_USE_ACCELERATE_ENDPOINT,
    S3_ADDRESSING_STYLE,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.tenants import Tenants
from open_webui.utils.auth import get_verified_user, get_admin_user

router = APIRouter()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

VISIBILITY_OPTIONS = {"public", "private"}

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    config = Config(
        s3={
            "use_accelerate_endpoint": S3_USE_ACCELERATE_ENDPOINT,
            "addressing_style": S3_ADDRESSING_STYLE,
        },
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )

    client_args = {
        "region_name": S3_REGION_NAME,
        "endpoint_url": S3_ENDPOINT_URL,
        "config": config,
    }

    if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
        client_args["aws_access_key_id"] = S3_ACCESS_KEY_ID
        client_args["aws_secret_access_key"] = S3_SECRET_ACCESS_KEY

    _s3_client = boto3.client("s3", **client_args)
    return _s3_client


def _sanitize_filename(filename: Optional[str]) -> str:
    base_name = os.path.basename(filename or "upload")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    return safe or "upload"


def _build_prefix(tenant_bucket: str, user_id: str, visibility: str) -> str:
    base = tenant_bucket
    if visibility == "private":
        base = posixpath.join(base, "users", user_id)
    return base


class UploadResponse(BaseModel):
    bucket: str
    key: str
    url: str
    visibility: Literal["public", "private"]
    original_filename: str
    stored_filename: str
    tenant_prefix: str
    tenant_id: str


class TenantInfo(BaseModel):
    id: str
    name: str
    s3_bucket: str


@router.get("/tenants", response_model=list[TenantInfo])
def list_tenants(admin=Depends(get_admin_user)):
    tenants = Tenants.get_tenants()
    return [TenantInfo(**tenant.model_dump()) for tenant in tenants]


@router.post("/", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    visibility: str = Form("public"),
    tenant_id: Optional[str] = Form(None),
    user=Depends(get_verified_user),
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

    target_tenant_id = user.tenant_id

    if tenant_id is not None:
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins may override the target tenant.",
            )
        target_tenant_id = tenant_id

    if not target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant.",
        )

    tenant = Tenants.get_tenant_by_id(target_tenant_id)
    if not tenant or not tenant.s3_bucket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant does not have an S3 bucket configured.",
        )

    normalized_visibility = (visibility or "public").lower()
    if normalized_visibility not in VISIBILITY_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visibility must be either 'public' or 'private'.",
        )

    safe_name = _sanitize_filename(file.filename)
    stored_filename = f"{uuid.uuid4().hex}_{safe_name}"
    tenant_prefix = _build_prefix(tenant.s3_bucket, user.id, normalized_visibility)
    object_key = posixpath.join(tenant_prefix, stored_filename)

    s3_client = _get_s3_client()

    extra_args = {}
    if file.content_type:
        extra_args["ContentType"] = file.content_type

    try:
        file.file.seek(0)
        if extra_args:
            s3_client.upload_fileobj(
                file.file, S3_BUCKET_NAME, object_key, ExtraArgs=extra_args
            )
        else:
            s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, object_key)
    except ClientError as exc:
        log.exception("Failed uploading file to S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to S3.",
        )

    return UploadResponse(
        bucket=S3_BUCKET_NAME,
        key=object_key,
        url=f"s3://{S3_BUCKET_NAME}/{object_key}",
        visibility=normalized_visibility,
        original_filename=safe_name,
        stored_filename=stored_filename,
        tenant_prefix=tenant_prefix,
        tenant_id=tenant.id,
    )
