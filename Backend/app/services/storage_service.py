import os
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageProvider(ABC):
    """
    Abstract interface for private document artifact storage.
    """
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        """Persist data bytes and return canonical storage key."""
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve data bytes for given storage key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an object exists at given storage key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete object at given storage key."""
        pass

class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider for development and testing environments.
    Stores private artifacts strictly outside of any publicly mounted directories.
    """
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        # Sanitize key and strictly prevent directory traversal
        clean_key = key.replace("\\", "/").lstrip("/")
        safe_path = os.path.abspath(os.path.join(self.base_dir, clean_key))
        if not safe_path.startswith(self.base_dir):
            raise ValueError(f"Directory traversal attack detected in storage key: '{key}'")
        return safe_path

    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        target_path = self._resolve_path(key)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        temp_path = f"{target_path}.tmp_{os.getpid()}"
        
        def _write():
            with open(temp_path, "wb") as f:
                f.write(data)
            os.replace(temp_path, target_path)

        await asyncio.to_thread(_write)
        return key

    async def get(self, key: str) -> bytes:
        target_path = self._resolve_path(key)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Object not found in local storage: '{key}'")
        
        def _read() -> bytes:
            with open(target_path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def exists(self, key: str) -> bool:
        target_path = self._resolve_path(key)
        return await asyncio.to_thread(os.path.exists, target_path)

    async def delete(self, key: str) -> bool:
        target_path = self._resolve_path(key)
        def _remove() -> bool:
            if os.path.exists(target_path):
                os.remove(target_path)
                return True
            return False
        return await asyncio.to_thread(_remove)

class S3StorageProvider(StorageProvider):
    """
    S3-compatible storage provider for Cloudflare R2 / AWS S3 in production.
    Communicates securely with private buckets using standard AWS signature v4.
    """
    def __init__(
        self,
        account_id: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        self.bucket_name = bucket_name or ""
        self._access_key_id = access_key_id or ""
        self._secret_access_key = secret_access_key or ""
        
        if endpoint_url:
            self.endpoint_url = endpoint_url
        elif account_id:
            self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        else:
            self.endpoint_url = ""

    def _get_client(self):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise RuntimeError(
                "The 'boto3' package is required for R2/S3 storage. "
                "Please run `pip install boto3` to enable cloud storage."
            )

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=Config(signature_version="s3v4")
        )

    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        def _upload():
            s3 = self._get_client()
            s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            return key
        return await asyncio.to_thread(_upload)

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            s3 = self._get_client()
            try:
                resp = s3.get_object(Bucket=self.bucket_name, Key=key)
                return resp["Body"].read()
            except Exception as e:
                logger.error(f"Failed to retrieve object '{key}' from S3/R2 bucket: {e}")
                raise FileNotFoundError(f"Object not found in R2 storage: '{key}'") from e
        return await asyncio.to_thread(_get)

    async def exists(self, key: str) -> bool:
        def _exists() -> bool:
            s3 = self._get_client()
            try:
                s3.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception:
                return False
        return await asyncio.to_thread(_exists)

    async def delete(self, key: str) -> bool:
        def _delete() -> bool:
            s3 = self._get_client()
            try:
                s3.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception:
                return False
        return await asyncio.to_thread(_delete)

def get_storage_service() -> StorageProvider:
    """
    Factory function returning the configured storage provider.
    Defaults to LocalStorageProvider for local development and automated testing.
    In production, prevents silent fallback to local ephemeral disk.
    """
    if settings.STORAGE_BACKEND == "r2":
        return S3StorageProvider(
            account_id=settings.R2_ACCOUNT_ID,
            access_key_id=settings.R2_ACCESS_KEY_ID,
            secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            bucket_name=settings.R2_BUCKET_NAME,
            endpoint_url=settings.R2_ENDPOINT_URL
        )
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: Ephemeral local storage cannot be used in production. "
            "Please configure Cloudflare R2 (STORAGE_BACKEND='r2') with required credentials."
        )
    return LocalStorageProvider(settings.PRIVATE_STORAGE_DIR)
