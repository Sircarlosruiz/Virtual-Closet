"""Seed script para modelos IA.

Sube thumbnails a MinIO (bucket model-thumbnails) e inserta filas en modelo_ia.
Si existe docs/imgs/modelo.jpeg, se usa para el primer modelo base; el resto usa placeholder.

Uso:
    cd backend
    uv run python scripts/seed_modelos_ia.py

Docker (monta docs/imgs o define SEED_IMGS_DIR):
    docker compose exec fastapi uv run python scripts/seed_modelos_ia.py
"""
import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiobotocore.session import get_session
from sqlalchemy import text
from core.config import settings
from core.database import async_session
from scripts.seed_paths import seed_image

MODELOS = [
    {"nombre": "María", "descripcion": "Mujer latina, 25-30 años, pelo oscuro", "plan_minimo": "base"},
    {"nombre": "Carlos", "descripcion": "Hombre latino, 30-35 años, pelo corto", "plan_minimo": "base"},
    {"nombre": "Sofía", "descripcion": "Mujer latina, 20-25 años, pelo largo rubio", "plan_minimo": "base"},
    {"nombre": "Diego", "descripcion": "Hombre latino, 25-30 años, barba", "plan_minimo": "base"},
    {"nombre": "Valentina Pro", "descripcion": "Mujer latina, premium, estudio profesional", "plan_minimo": "pro"},
    {"nombre": "Alejandro Pro", "descripcion": "Hombre latino, premium, estudio profesional", "plan_minimo": "pro"},
]


async def create_placeholder_image() -> bytes:
    """Genera una imagen placeholder simple (1x1 pixel blanco en JPG)."""
    try:
        from PIL import Image
        img = Image.new("RGB", (400, 600), color=(220, 220, 220))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\x27 \",#\x1c\x1c(7teletext:7teletext:teletext(7teletext:\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4\xff\xd9"


async def seed_modelos_ia():
    session = get_session()

    async with session.create_client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
    ) as client:
        buckets = await client.list_buckets()
        bucket_names = [b["Name"] for b in buckets.get("Buckets", [])]

        for bucket in [settings.MINIO_BUCKET_MODEL_THUMBNAILS]:
            if bucket not in bucket_names:
                await client.create_bucket(Bucket=bucket)

        placeholder = await create_placeholder_image()
        modelo_ejemplo = seed_image("modelo.jpeg")

        for i, modelo in enumerate(MODELOS, start=1):
            model_id = f"{i:04d}"
            key = f"{model_id}.jpg"
            use_ejemplo = i == 1 and modelo_ejemplo is not None
            body = modelo_ejemplo.read_bytes() if use_ejemplo else placeholder
            fuente = "docs/imgs/modelo.jpeg" if use_ejemplo else "placeholder"
            try:
                await client.put_object(
                    Bucket=settings.MINIO_BUCKET_MODEL_THUMBNAILS,
                    Key=key,
                    Body=body,
                    ContentType="image/jpeg",
                )
                print(f"  Subida imagen: {key} ({fuente})")
            except Exception as e:
                print(f"  Error subiendo {key}: {e}")

    async with async_session() as db:
        existing = await db.execute(text("SELECT COUNT(*) FROM modelo_ia"))
        count = existing.scalar()
        if count > 0:
            print(f"  Ya existen {count} modelos IA. Saltando seed.")
            return

        for i, modelo in enumerate(MODELOS, start=1):
            model_id = f"{i:04d}"
            await db.execute(
                text(
                    """
                    INSERT INTO modelo_ia (id, nombre, descripcion, thumbnail_key, plan_minimo)
                    VALUES (gen_random_uuid(), :nombre, :descripcion, :thumbnail_key, :plan_minimo)
                    """
                ),
                {
                    "nombre": modelo["nombre"],
                    "descripcion": modelo["descripcion"],
                    "thumbnail_key": f"{model_id}.jpg",
                    "plan_minimo": modelo["plan_minimo"],
                },
            )
        await db.commit()
        print(f"  Insertados {len(MODELOS)} modelos IA en la BD.")


if __name__ == "__main__":
    print("Seed modelos IA...")
    asyncio.run(seed_modelos_ia())
    print("Seed completado.")
