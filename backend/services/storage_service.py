from aiobotocore.session import get_session
from botocore.config import Config
from core.config import settings


class StorageService:
    def __init__(self) -> None:
        self._session = get_session()
        self._internal_endpoint = settings.MINIO_ENDPOINT
        self._public_endpoint = settings.MINIO_PUBLIC_ENDPOINT
        self._access_key = settings.MINIO_ACCESS_KEY
        self._secret_key = settings.MINIO_SECRET_KEY
        self._bucket = settings.MINIO_BUCKET_ORIGINALS
        self._config = Config(signature_version="s3v4")
        self._buckets = {
            "originals": settings.MINIO_BUCKET_ORIGINALS,
            "generated": settings.MINIO_BUCKET_GENERATED,
            "thumbnails": settings.MINIO_BUCKET_THUMBNAILS,
            "model-thumbnails": settings.MINIO_BUCKET_MODEL_THUMBNAILS,
        }

    async def generate_upload_url(self, key: str, ttl_seconds: int = 900, bucket_override: str | None = None) -> str:
        bucket = self._buckets.get(bucket_override, self._bucket) if bucket_override else self._bucket
        async with self._session.create_client(
            "s3",
            endpoint_url=self._public_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
            config=self._config,
        ) as client:
            url = await client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl_seconds,
                HttpMethod="PUT",
            )
        return url

    async def generate_download_url(self, key: str, ttl_seconds: int = 86400, bucket_override: str | None = None) -> str:
        bucket = self._buckets.get(bucket_override, self._bucket) if bucket_override else self._bucket
        async with self._session.create_client(
            "s3",
            endpoint_url=self._public_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
            config=self._config,
        ) as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            )
        return url

    async def delete_object(self, key: str) -> None:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
            config=self._config,
        ) as client:
            await client.delete_object(Bucket=self._bucket, Key=key)

    async def get_object_bytes(self, key: str, bucket_override: str | None = None) -> bytes:
        bucket = self._buckets.get(bucket_override, self._bucket) if bucket_override else self._bucket
        async with self._session.create_client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
            config=self._config,
        ) as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            return await response["Body"].read()

    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/jpeg",
        bucket_override: str | None = None,
    ) -> None:
        bucket = self._buckets.get(bucket_override, self._bucket) if bucket_override else self._bucket
        async with self._session.create_client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
            config=self._config,
        ) as client:
            await client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

    def get_object_bytes_sync(self, key: str, bucket_override: str | None = None) -> bytes:
        import boto3
        bucket = self._buckets.get(bucket_override, self._bucket) if bucket_override else self._bucket
        client = boto3.client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
        )
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def upload_bytes_sync(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/jpeg",
        bucket_override: str | None = None,
    ) -> None:
        import boto3
        bucket = self._buckets.get(bucket_override, self._bucket) if bucket_override else self._bucket
        client = boto3.client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_secret_access_key=self._secret_key,
            aws_access_key_id=self._access_key,
        )
        client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
