"""Crea una prenda de ejemplo con producto_1.jpeg en MinIO (bucket originals).

Requiere un mayorista existente (regístrate antes o pasa el email).

Uso:
    cd backend
    uv run python scripts/seed_prenda_ejemplo.py tu@email.com

Docker:
    docker compose exec fastapi uv run python scripts/seed_prenda_ejemplo.py tu@email.com
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiobotocore.session import get_session
from sqlalchemy import select, text

from core.config import settings
from core.database import async_session
from models.mayorista import Mayorista
from scripts.seed_paths import seed_image
from services.storage_service import StorageService

PRODUCTO_FILE = "producto_1.jpeg"
PRENDA_NOMBRE = "Camiseta ejemplo (seed)"


async def seed_prenda_ejemplo(email: str) -> None:
    img_path = seed_image(PRODUCTO_FILE)
    if not img_path:
        raise FileNotFoundError(
            f"No se encontró {PRODUCTO_FILE}. Colócalo en docs/imgs/ "
            f"(o define SEED_IMGS_DIR)."
        )

    image_bytes = img_path.read_bytes()
    content_type = "image/jpeg"

    async with async_session() as db:
        result = await db.execute(select(Mayorista).where(Mayorista.email == email))
        mayorista = result.scalar_one_or_none()
        if not mayorista:
            raise RuntimeError(
                f"No hay mayorista con email '{email}'. Regístrate en la app primero."
            )

        existing = await db.execute(
            text("SELECT id FROM prenda WHERE mayorista_id = :mid AND nombre = :nombre LIMIT 1"),
            {"mid": mayorista.id, "nombre": PRENDA_NOMBRE},
        )
        if existing.scalar_one_or_none():
            print(f"  Ya existe la prenda de ejemplo para {email}. Saltando.")
            return

        mayorista_id = mayorista.id
        prenda_id = uuid4()
        object_key = f"{mayorista_id}/{prenda_id}/original.jpg"

    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
    ) as client:
        buckets = await client.list_buckets()
        bucket_names = [b["Name"] for b in buckets.get("Buckets", [])]
        bucket = settings.MINIO_BUCKET_ORIGINALS
        if bucket not in bucket_names:
            await client.create_bucket(Bucket=bucket)

        await client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=image_bytes,
            ContentType=content_type,
        )
        print(f"  Subida prenda a MinIO: {bucket}/{object_key}")

    storage = StorageService()
    imagen_url = await storage.generate_download_url(object_key)

    async with async_session() as db:
        await db.execute(
            text(
                """
                INSERT INTO prenda (id, mayorista_id, nombre, imagen_original_url, estado)
                VALUES (:id, :mayorista_id, :nombre, :imagen_url, 'lista')
                """
            ),
            {
                "id": prenda_id,
                "mayorista_id": mayorista_id,
                "nombre": PRENDA_NOMBRE,
                "imagen_url": imagen_url,
            },
        )
        await db.commit()
        print(f"  Prenda insertada: {prenda_id} ({PRENDA_NOMBRE})")
        print(f"  Abre: /dashboard/generacion/model-selector?prendaId={prenda_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: uv run python scripts/seed_prenda_ejemplo.py <email-mayorista>")
        sys.exit(1)
    print("Seed prenda de ejemplo...")
    asyncio.run(seed_prenda_ejemplo(sys.argv[1]))
    print("Seed completado.")
