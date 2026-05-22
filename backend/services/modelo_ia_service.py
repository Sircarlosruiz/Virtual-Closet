from uuid import UUID
from services.storage_service import StorageService
from repositories.modelo_ia_repo import ModeloIARepository
from models.modelo_ia import ModeloIA


class ModeloIAService:
    def __init__(self, repo: ModeloIARepository, storage: StorageService) -> None:
        self._repo = repo
        self._storage = storage

    async def get_by_plan(self, plan: str, mayorista_id: UUID) -> list[dict]:
        modelos = await self._repo.get_by_plan(plan, mayorista_id)
        result = []
        for m in modelos:
            thumbnail_url = await self._storage.generate_download_url(
                key=f"{m.thumbnail_key}",
                ttl_seconds=86400,
                bucket_override="model-thumbnails",
            )
            result.append({
                "id": m.id,
                "nombre": m.nombre,
                "descripcion": m.descripcion,
                "thumbnail_url": thumbnail_url,
                "plan_minimo": m.plan_minimo,
            })
        return result

    async def get_by_id(self, modelo_id: UUID) -> ModeloIA | None:
        return await self._repo.get_by_id(modelo_id)

    async def generate_upload_url(self, extension: str) -> tuple[str, str, str]:
        import uuid
        modelo_id = str(uuid.uuid4())
        object_key = f"custom/{modelo_id}/original.{extension}"
        upload_url = await self._storage.generate_upload_url(
            key=object_key,
            ttl_seconds=900,
            bucket_override="model-thumbnails",
        )
        return modelo_id, upload_url, object_key

    async def create_modelo(
        self,
        mayorista_id: UUID,
        modelo_id: UUID,
        nombre: str,
        descripcion: str | None,
        object_key: str,
    ) -> dict:
        modelo = ModeloIA(
            id=modelo_id,
            mayorista_id=mayorista_id,
            nombre=nombre,
            descripcion=descripcion,
            thumbnail_key=object_key,
            plan_minimo="base",
        )
        created = await self._repo.create(modelo)
        thumbnail_url = await self._storage.generate_download_url(
            key=object_key,
            ttl_seconds=86400,
            bucket_override="model-thumbnails",
        )
        return {
            "id": created.id,
            "nombre": created.nombre,
            "descripcion": created.descripcion,
            "thumbnail_url": thumbnail_url,
            "plan_minimo": created.plan_minimo,
        }
