import logging
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from open_webui.config import (
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_REGION_NAME,
    S3_ENDPOINT_URL,
    S3_USE_ACCELERATE_ENDPOINT,
    S3_ADDRESSING_STYLE,
)

log = logging.getLogger(__name__)

_s3_client = None


def get_s3_client():
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


def upload_fileobj(file, bucket: str, key: str, extra_args: Optional[dict] = None):
    client = get_s3_client()
    file.seek(0)
    if extra_args:
        client.upload_fileobj(file, bucket, key, ExtraArgs=extra_args)
    else:
        client.upload_fileobj(file, bucket, key)


def delete_object(bucket: str, key: str):
    client = get_s3_client()
    client.delete_object(Bucket=bucket, Key=key)


def object_exists(bucket: str, key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey", "NotFound", "NoSuchBucket"):
            return False
        if error_code in ("403", "AccessDenied", "Forbidden"):
            try:
                resp = client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
                contents = resp.get("Contents", [])
                return any(obj.get("Key") == key for obj in contents)
            except ClientError:
                return False
        return True


def generate_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
