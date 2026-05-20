from uuid import UUID
from fastapi import HTTPException
from models.generacion import Generacion
from repositories.generacion_repo import GeneracionRepository
from repositories.modelo_ia_repo import ModeloIARepository
from repositories.prenda_repo import PrendaRepository
from services.storage_service import StorageService


class GeneracionNoEncontradaError(Exception):
    pass


class CuotaExcedidaError(Exception):
    pass


class GeneracionService:
    def __init__(
        self,
        generacion_repo: GeneracionRepository,
        modelo_ia_repo: ModeloIARepository,
        prenda_repo: PrendaRepository,
        storage: StorageService,
    ) -> None:
        self._generacion_repo = generacion_repo
        self._modelo_ia_repo = modelo_ia_repo
        self._prendas_repo = prenda_repo
        self._storage = storage

    async def crear_generacion(
        self,
        mayorista_id: UUID,
        prenda_id: UUID,
        modelo_ia_id: UUID,
        plan: str,
    ) -> Generacion:
        prenda = await self._prendas_repo.get_by_id(prenda_id, mayorista_id)
        if not prenda:
            raise HTTPException(status_code=404, detail="Prenda no encontrada")

        modelo = await self._modelo_ia_repo.get_by_id(modelo_ia_id)
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo IA no encontrado")

        plan_order = {"base": 0, "pro": 1}
        if plan_order.get(modelo.plan_minimo, 0) > plan_order.get(plan, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere plan {modelo.plan_minimo} para este modelo",
            )

        generacion = Generacion(
            mayorista_id=mayorista_id,
            prenda_id=prenda_id,
            modelo_ia_id=modelo_ia_id,
            estado="procesando",
        )
        return await self._generacion_repo.create(generacion)

    async def get_generacion(self, generacion_id: UUID, mayorista_id: UUID) -> Generacion:
        generacion = await self._generacion_repo.get_by_id(generacion_id)
        if not generacion or generacion.mayorista_id != mayorista_id:
            raise HTTPException(status_code=404, detail="Generación no encontrada")
        return generacion

    async def get_generaciones_by_prenda(self, prenda_id: UUID, mayorista_id: UUID) -> list[Generacion]:
        prenda = await self._prendas_repo.get_by_id(prenda_id, mayorista_id)
        if not prenda:
            raise HTTPException(status_code=404, detail="Prenda no encontrada")
        return await self._generacion_repo.list_by_prenda(prenda_id)

    async def get_presigned_urls(self, generacion: Generacion) -> dict:
        result = {}
        if generacion.imagen_generada_key:
            result["imagen_url"] = await self._storage.generate_download_url(
                key=generacion.imagen_generada_key,
                bucket_override="generated",
            )
        if generacion.thumbnail_key:
            result["thumbnail_url"] = await self._storage.generate_download_url(
                key=generacion.thumbnail_key,
                bucket_override="thumbnails",
            )
        return result
