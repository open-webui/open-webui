"""
Copy local upload files into the NCP Object Storage bucket configured for
the app. After this finishes successfully, set STORAGE_PROVIDER=s3 in
.env so the running app reads/writes new uploads against the bucket.

Usage:

    UPLOADS_DIR=/home/shared/hyu-math/backend/open_webui/data/uploads \\
    S3_ENDPOINT_URL=https://kr.object.ncloudstorage.com \\
    S3_REGION_NAME=kr-standard \\
    S3_BUCKET_NAME=hyu-math-uploads \\
    S3_ACCESS_KEY_ID=... \\
    S3_SECRET_ACCESS_KEY=... \\
        python3 scripts/migration/migrate_uploads_to_s3.py

The script preserves directory structure as object keys (e.g.
uploads/foo/bar.pdf -> foo/bar.pdf in the bucket). Re-runs are safe: it
overwrites existing objects.
"""

import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config


def main() -> int:
    uploads = Path(os.environ.get("UPLOADS_DIR", ""))
    bucket = os.environ.get("S3_BUCKET_NAME")
    if not uploads.is_dir() or not bucket:
        print("ERROR: set UPLOADS_DIR (existing dir) and S3_BUCKET_NAME", file=sys.stderr)
        return 1

    client = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        region_name=os.environ["S3_REGION_NAME"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        config=Config(s3={"addressing_style": "path"}),
    )

    n_files = n_bytes = 0
    for f in uploads.rglob("*"):
        if not f.is_file():
            continue
        key = f.relative_to(uploads).as_posix()
        size = f.stat().st_size
        print(f"  {key} ({size} bytes)")
        client.upload_file(str(f), bucket, key)
        n_files += 1
        n_bytes += size

    print(f"\nDone. {n_files} files / {n_bytes / 1024 / 1024:.2f} MB uploaded to s3://{bucket}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
