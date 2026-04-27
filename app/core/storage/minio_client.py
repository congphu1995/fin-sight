"""Async wrapper around the (sync) MinIO Python SDK.

The SDK is sync-only, so every call is dispatched to a thread via asyncio.to_thread.
This client raises StorageError on failure; the caller decides how to handle it.
"""

import asyncio
import io
from datetime import timedelta
from typing import Protocol

from minio import Minio
from minio.error import S3Error

from app.core.exceptions import StorageError


class MinioClientProtocol(Protocol):
    """Subset of MinioClient used by services. Lets tests substitute a fake."""

    bucket: str

    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None: ...

    async def get_object(self, key: str) -> bytes: ...

    async def stat_object(self, key: str) -> bool: ...

    async def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str: ...


class MinioClient:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket = bucket

    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        try:
            await asyncio.to_thread(
                self._client.put_object,
                bucket_name=self.bucket,
                object_name=key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            raise StorageError(f"put_object {key}: {exc}") from exc

    async def get_object(self, key: str) -> bytes:
        def _read() -> bytes:
            response = self._client.get_object(self.bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            return await asyncio.to_thread(_read)
        except S3Error as exc:
            raise StorageError(f"get_object {key}: {exc}") from exc

    async def stat_object(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.stat_object, self.bucket, key)
            return True
        except S3Error:
            return False

    async def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        try:
            return await asyncio.to_thread(
                self._client.presigned_get_object,
                self.bucket,
                key,
                expires=timedelta(seconds=expires_seconds),
            )
        except S3Error as exc:
            raise StorageError(f"presigned_get_object {key}: {exc}") from exc

    async def ensure_bucket(self) -> None:
        try:
            exists = await asyncio.to_thread(self._client.bucket_exists, self.bucket)
            if not exists:
                await asyncio.to_thread(self._client.make_bucket, self.bucket)
        except S3Error as exc:
            raise StorageError(f"ensure_bucket {self.bucket}: {exc}") from exc
