import io
import json
from uuid import UUID

from core.celery_app import app
from core.config import settings
from services.storage_service import StorageService
from PIL import Image


def _get_storage() -> StorageService:
    return StorageService()


def _sync_send_ws(mayorista_id: UUID, message: dict) -> None:
    """Send WebSocket message synchronously using sync wrapper."""
    import asyncio
    from services.connection_manager import manager
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            manager.send(mayorista_id, json.dumps(message))
        )
        loop.close()
    except Exception:
        pass


def _run_vton_provider(garment_bytes: bytes, model_bytes: bytes) -> bytes:
    """Run async VTON provider synchronously."""
    import asyncio
    from services.vton import get_provider
    provider = get_provider()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(provider.generate(garment_bytes, model_bytes))
        return result
    finally:
        loop.close()


@app.task(
    bind=True,
    max_retries=3,
    acks_late=True,
    queue="vton.generation.normal",
)
def generate_vton_task(self, generacion_id: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.generacion import Generacion
    from models.prenda import Prenda
    from models.modelo_ia import ModeloIA

    storage = _get_storage()

    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)
    Session = sessionmaker(engine)
    session = Session()

    try:
        generacion = session.query(Generacion).filter(Generacion.id == UUID(generacion_id)).first()
        if not generacion:
            raise ValueError(f"Generacion {generacion_id} not found")

        prenda = session.query(Prenda).filter(Prenda.id == generacion.prenda_id).first()
        if not prenda:
            raise ValueError(f"Prenda {generacion.prenda_id} not found")

        modelo = session.query(ModeloIA).filter(ModeloIA.id == generacion.modelo_ia_id).first()
        if not modelo:
            raise ValueError(f"ModeloIA {generacion.modelo_ia_id} not found")

        garment_key = f"{generacion.mayorista_id}/{prenda.id}/original.jpg"
        model_key = modelo.thumbnail_key

        garment_bytes = storage.get_object_bytes_sync(garment_key)
        model_bytes = storage.get_object_bytes_sync(model_key, bucket_override="model-thumbnails")

        result_bytes = _run_vton_provider(garment_bytes, model_bytes)

        generated_key = f"{generacion.mayorista_id}/{generacion.id}.jpg"
        thumbnail_key = f"{generacion.mayorista_id}/{generacion.id}.jpg"

        storage.upload_bytes_sync(generated_key, result_bytes, bucket_override="generated")

        img = Image.open(io.BytesIO(result_bytes))
        img.thumbnail((400, 400))
        thumb_buf = io.BytesIO()
        img.save(thumb_buf, format="JPEG")
        storage.upload_bytes_sync(thumbnail_key, thumb_buf.getvalue(), bucket_override="thumbnails")

        generacion.estado = "lista"
        generacion.imagen_generada_key = generated_key
        generacion.thumbnail_key = thumbnail_key
        session.commit()

        _sync_send_ws(generacion.mayorista_id, {
            "type": "generacion_completada",
            "generacion_id": generacion_id,
        })

    except Exception as exc:
        try:
            session.rollback()
            generacion = session.query(Generacion).filter(Generacion.id == UUID(generacion_id)).first()
            if generacion:
                generacion.estado = "error"
                generacion.error_message = str(exc)
                session.commit()

                _sync_send_ws(generacion.mayorista_id, {
                    "type": "generacion_error",
                    "generacion_id": generacion_id,
                    "error": str(exc),
                })
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            raise self.exc(exc)

    finally:
        session.close()
