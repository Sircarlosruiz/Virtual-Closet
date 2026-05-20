from aiobotocore.session import get_session
from core.config import settings


class StorageService:
    def __init__(self) -> None:
        self._session = get_session()
        self._endpoint = settings.MINIO_ENDPOINT
        self._access_key = settings.MINIO_ACCESS_KEY
        self._secret_key = settings.MINIO_SECRET_KEY
        self._bucket = settings.MINIO_BUCKET_ORIGINALS

    async def generate_upload_url(self, key: str, ttl_seconds: int = 900) -> str:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
        ) as client:
            url = await client.generate_presigned_url(
                "put_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            )
        return self._replace_host(url)

    async def generate_download_url(self, key: str, ttl_seconds: int = 86400) -> str:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
        ) as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            )
        return self._replace_host(url)

    async def delete_object(self, key: str) -> None:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
        ) as client:
            await client.delete_object(Bucket=self._bucket, Key=key)

    @staticmethod
    def _replace_host(url: str) -> str:
        return url.replace("http://minio:9000", "http://localhost:9000")
