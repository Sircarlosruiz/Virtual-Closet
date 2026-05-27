from aiobotocore.session import get_session

from core.config import settings


class MinIOClient:
    """Async MinIO client wrapper using aiobotocore."""

    def __init__(self) -> None:
        self._session = get_session()

    async def _get_client(self):
        return self._session.create_client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
        )

    async def upload_file(
        self, bucket: str, key: str, data: bytes, content_type: str
    ) -> None:
        """Upload raw bytes to MinIO."""
        async with await self._get_client() as client:
            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

    async def get_presigned_url(
        self, bucket: str, key: str, expires: int = 900
    ) -> str:
        """Generate a pre-signed URL for reading an object (default 15 min TTL)."""
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires,
            )
            # Replace internal endpoint with public endpoint for browser access
            url = url.replace(
                settings.MINIO_ENDPOINT.rstrip("/"),
                settings.MINIO_PUBLIC_ENDPOINT.rstrip("/"),
            )
            return url

    async def file_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in MinIO."""
        async with await self._get_client() as client:
            try:
                await client.head_object(Bucket=bucket, Key=key)
                return True
            except client.exceptions.ClientError:
                return False
