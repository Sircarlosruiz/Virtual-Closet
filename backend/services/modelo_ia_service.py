from services.storage_service import StorageService
from repositories.modelo_ia_repo import ModeloIARepository


class ModeloIAService:
    def __init__(self, repo: ModeloIARepository, storage: StorageService) -> None:
        self._repo = repo
        self._storage = storage

    async def get_by_plan(self, plan: str) -> list[dict]:
        modelos = await self._repo.get_by_plan(plan)
        result = []
        for m in modelos:
            thumbnail_url = await self._storage.generate_download_url(
                key=f"{m.thumbnail_key}",
                ttl_seconds=86400,
                bucket_override=None,
            )
            result.append({
                "id": m.id,
                "nombre": m.nombre,
                "descripcion": m.descripcion,
                "thumbnail_url": thumbnail_url,
                "plan_minimo": m.plan_minimo,
            })
        return result

    async def get_by_id(self, modelo_id):
        return await self._repo.get_by_id(modelo_id)
