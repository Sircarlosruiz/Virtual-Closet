from core.config import settings


def minio_bucket_names() -> list[str]:
    return [
        settings.MINIO_BUCKET_ORIGINALS,
        settings.MINIO_BUCKET_GENERATED,
        settings.MINIO_BUCKET_THUMBNAILS,
        settings.MINIO_BUCKET_MODEL_THUMBNAILS,
    ]


def ensure_minio_buckets_sync() -> None:
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
    )
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    for bucket in minio_bucket_names():
        if bucket not in existing:
            client.create_bucket(Bucket=bucket)


async def ensure_minio_buckets() -> None:
    from aiobotocore.session import get_session

    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
    ) as client:
        buckets = await client.list_buckets()
        bucket_names = {b["Name"] for b in buckets.get("Buckets", [])}
        for bucket in minio_bucket_names():
            if bucket not in bucket_names:
                await client.create_bucket(Bucket=bucket)
