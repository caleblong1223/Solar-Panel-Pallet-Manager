from __future__ import annotations

import hashlib
import mimetypes
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


class StorageError(RuntimeError):
    pass


def _build_import_object_key(batch_id: int, filename: str, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    safe_name = os.path.basename(filename) or f"batch-{batch_id}.bin"
    return f"imports/{current.year:04d}/{current.month:02d}/{batch_id}/{safe_name}"


def upload_import_source(batch_id: int, filename: str, content: bytes) -> tuple[str, str]:
    checksum = hashlib.sha256(content).hexdigest()
    object_key = _build_import_object_key(batch_id=batch_id, filename=filename)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    client = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )

    try:
        client.put_object(
            Bucket=settings.minio_bucket_imports,
            Key=object_key,
            Body=content,
            ContentType=content_type,
            Metadata={"checksum-sha256": checksum},
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"Failed to upload import source: {exc}") from exc

    return object_key, checksum


def upload_export_artifact(
    export_id: int,
    pallet_id: int,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> tuple[str, str]:
    checksum = hashlib.sha256(content).hexdigest()
    now = datetime.now(timezone.utc)
    object_key = f"exports/{now.year:04d}/{now.month:02d}/{pallet_id}/{export_id}/{os.path.basename(filename)}"
    resolved_content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    client = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )

    try:
        client.put_object(
            Bucket=settings.minio_bucket_exports,
            Key=object_key,
            Body=content,
            ContentType=resolved_content_type,
            Metadata={"checksum-sha256": checksum},
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"Failed to upload export artifact: {exc}") from exc

    return object_key, checksum


def generate_export_download_url(object_key: str, expires_in_seconds: int = 900) -> str:
    client = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.minio_bucket_exports, "Key": object_key},
            ExpiresIn=expires_in_seconds,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"Failed to generate export download URL: {exc}") from exc
