import logging
import os
import posixpath
import re
import uuid
from datetime import datetime
from typing import Literal, Optional, List

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
from open_webui.routers.luxor import rag_master_request
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


class PublicFile(BaseModel):
    key: str
    size: int
    last_modified: datetime
    url: str
    tenant_id: str


class IngestUploadRequest(BaseModel):
    key: str


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


@router.get("/files", response_model=List[PublicFile])
def list_files(
    path: Optional[str] = None,
    tenant_id: Optional[str] = None,
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
                detail="Only admins may view other tenants' files.",
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

    bucket_prefix = tenant.s3_bucket.rstrip("/")

    if path:
        normalized_path = path.rstrip("/")
    else:
        normalized_path = bucket_prefix

    if not normalized_path.startswith(bucket_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path for the selected tenant.",
        )

    normalized_path_with_slash = normalized_path + "/"
    bucket_public_prefix = bucket_prefix + "/"

    relative = (
        normalized_path_with_slash[len(bucket_public_prefix) :]
        if normalized_path_with_slash.startswith(bucket_public_prefix)
        else ""
    )

    if relative.startswith("users/"):
        remainder = relative[len("users/") :]
        target_user_id = remainder.split("/", 1)[0] if remainder else ""
        if not target_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid private path.",
            )
        if user.role != "admin" and user.id != target_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users' private files.",
            )
    else:
        target_user_id = None

    list_prefix = normalized_path_with_slash
    private_prefix = bucket_public_prefix + "users/"

    s3_client = _get_s3_client()
    paginator = s3_client.get_paginator("list_objects_v2")
    files: List[PublicFile] = []

    try:
        for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=list_prefix):
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if not key or key.endswith("/"):
                    continue
                if relative == "" and key.startswith(private_prefix):
                    continue

                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": S3_BUCKET_NAME, "Key": key},
                    ExpiresIn=3600,
                )

                files.append(
                    PublicFile(
                        key=key,
                        size=obj.get("Size", 0),
                        last_modified=obj.get("LastModified"),
                        url=url,
                        tenant_id=tenant.id,
                    )
                )
    except ClientError as exc:
        log.exception("Failed to list public files from S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files from S3.",
        )

    return files


@router.post("/ingest")
async def ingest_uploaded_file(
    form_data: IngestUploadRequest,
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

    if not form_data.key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key is required.",
        )

    payload = {
        "task": "ingest-upload",
        "bucket": S3_BUCKET_NAME,
        "key": form_data.key,
    }

    try:
        response = await rag_master_request(payload)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        log.exception("Failed to trigger ingestion for %s: %s", form_data.key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger ingestion for the uploaded file.",
        )

    return response
