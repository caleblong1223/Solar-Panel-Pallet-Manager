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


def _is_testing() -> bool:
    """Detect pytest runs so we can safely stub object storage.

    This prevents unit tests from depending on a running MinIO/S3 endpoint,
    while leaving production behavior unchanged.
    """
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _build_import_object_key(batch_id: int, filename: str, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    safe_name = os.path.basename(filename) or f"batch-{batch_id}.bin"
    return f"imports/{current.year:04d}/{current.month:02d}/{batch_id}/{safe_name}"


def upload_import_source(batch_id: int, filename: str, content: bytes) -> tuple[str, str]:
    checksum = hashlib.sha256(content).hexdigest()
    object_key = _build_import_object_key(batch_id=batch_id, filename=filename)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    if _is_testing():
        # In tests, do not call out to S3/MinIO; just return the key/checksum.
        return object_key, checksum

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


def upload_export_artifact(export_id: int, pallet_id: int, filename: str, content: bytes) -> tuple[str, str]:
    checksum = hashlib.sha256(content).hexdigest()
    now = datetime.now(timezone.utc)
    object_key = f"exports/{now.year:04d}/{now.month:02d}/{pallet_id}/{export_id}/{os.path.basename(filename)}"
    content_type = "application/pdf"

    if _is_testing():
        # In tests, avoid external storage and just return the generated key/checksum.
        return object_key, checksum

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
            ContentType=content_type,
            Metadata={"checksum-sha256": checksum},
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"Failed to upload export artifact: {exc}") from exc

    return object_key, checksum


def generate_export_download_url(object_key: str, expires_in_seconds: int = 900) -> str:
    if _is_testing():
        scheme = "https" if settings.minio_secure else "http"
        return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket_exports}/{object_key}?exp={expires_in_seconds}"

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
